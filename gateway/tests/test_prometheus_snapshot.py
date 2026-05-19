import math

from benchmark.collect_prometheus_snapshot import (
    PROMETHEUS_QUERIES,
    normalize_query_response,
    parse_prometheus_value,
)
from benchmark.sample_prometheus_timeseries import sample_values, summarize_points


def test_parse_prometheus_value_converts_numeric_string() -> None:
    assert parse_prometheus_value([1779219767.0, "12.34"]) == 12.34
    assert math.isnan(parse_prometheus_value([1779219767.0, "NaN"]))
    assert parse_prometheus_value(["bad"]) is None


def test_normalize_query_response_extracts_vector_samples() -> None:
    payload = {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [
                {
                    "metric": {"model_name": "qwen"},
                    "value": [1779219767.0, "42"],
                }
            ],
        },
    }

    result = normalize_query_response(payload)

    assert result == {
        "status": "success",
        "result_type": "vector",
        "samples": [
            {
                "metric": {"model_name": "qwen"},
                "timestamp": 1779219767.0,
                "value": 42.0,
            }
        ],
    }


def test_normalize_query_response_handles_prometheus_error() -> None:
    result = normalize_query_response({"status": "error", "error": "bad query"})

    assert result["status"] == "error"
    assert result["samples"] == []
    assert result["error"] == "bad query"


def test_vllm_kv_cache_query_supports_current_and_legacy_metric_names() -> None:
    query = PROMETHEUS_QUERIES["vllm_kv_cache_usage_percent"]

    assert "vllm:kv_cache_usage_perc" in query
    assert "vllm:gpu_cache_usage_perc" in query


def test_sample_values_extracts_numeric_values_only() -> None:
    samples = [
        {"value": 1.0},
        {"value": 2},
        {"value": None},
        {"value": "3"},
        "bad",
    ]

    assert sample_values(samples) == [1.0, 2.0]


def test_summarize_points_ignores_non_finite_values() -> None:
    points = [
        {"samples": [{"value": 1.0}, {"value": float("nan")}]},
        {"samples": [{"value": 3.0}]},
        {"samples": []},
    ]

    assert summarize_points(points) == {
        "sample_count": 2,
        "point_count": 3,
        "min": 1.0,
        "mean": 2.0,
        "max": 3.0,
        "last": 3.0,
    }


def test_summarize_points_handles_empty_samples() -> None:
    assert summarize_points([{"samples": []}]) == {
        "sample_count": 0,
        "point_count": 1,
        "min": None,
        "mean": None,
        "max": None,
        "last": None,
    }
