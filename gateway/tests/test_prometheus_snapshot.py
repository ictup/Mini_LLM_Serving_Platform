import math

from benchmark.collect_prometheus_snapshot import (
    normalize_query_response,
    parse_prometheus_value,
)


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
