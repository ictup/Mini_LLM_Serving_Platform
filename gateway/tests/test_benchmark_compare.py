from pathlib import Path

import pytest

from benchmark.compare_results import (
    BenchmarkRun,
    PrometheusSnapshot,
    PrometheusTimeSeries,
    build_comparison_markdown,
    compare_runs,
    delta_percent,
    load_benchmark_run,
    load_prometheus_snapshot,
    load_prometheus_timeseries,
)


def test_compare_runs_matches_shared_concurrency_levels() -> None:
    direct_run = BenchmarkRun(
        path=Path("direct.json"),
        payload={
            "summaries": [
                {"concurrency": 1, "rps": 10.0},
                {"concurrency": 2, "rps": 18.0},
            ]
        },
    )
    gateway_run = BenchmarkRun(
        path=Path("gateway.json"),
        payload={
            "summaries": [
                {"concurrency": 2, "rps": 16.0},
                {"concurrency": 4, "rps": 24.0},
            ]
        },
    )

    rows = compare_runs(direct_run, gateway_run)

    assert [row.concurrency for row in rows] == [2]
    assert rows[0].direct_summary["rps"] == 18.0
    assert rows[0].gateway_summary["rps"] == 16.0


def test_compare_runs_rejects_results_without_shared_concurrency() -> None:
    direct_run = BenchmarkRun(path=Path("direct.json"), payload={"summaries": [{"concurrency": 1}]})
    gateway_run = BenchmarkRun(
        path=Path("gateway.json"),
        payload={"summaries": [{"concurrency": 2}]},
    )

    with pytest.raises(ValueError, match="no shared concurrency"):
        compare_runs(direct_run, gateway_run)


def test_build_comparison_markdown_renders_overhead_values() -> None:
    direct_run = BenchmarkRun(
        path=Path("benchmark/results/direct.json"),
        payload={
            "base_url": "http://localhost:8000/v1",
            "model": "Qwen/Qwen2.5-1.5B-Instruct",
            "stream": True,
            "requests_per_level": 10,
            "summaries": [
                {
                    "concurrency": 1,
                    "rps": 10.0,
                    "p50_latency_ms": 100.0,
                    "p95_latency_ms": 150.0,
                    "p99_latency_ms": 190.0,
                    "p50_ttft_ms": 40.0,
                    "p95_ttft_ms": 60.0,
                    "error_rate": 0.0,
                }
            ],
        },
    )
    gateway_run = BenchmarkRun(
        path=Path("benchmark/results/gateway.json"),
        payload={
            "base_url": "http://localhost:8080/v1",
            "model": "qwen-small",
            "stream": True,
            "requests_per_level": 10,
            "summaries": [
                {
                    "concurrency": 1,
                    "rps": 8.0,
                    "p50_latency_ms": 120.0,
                    "p95_latency_ms": 180.0,
                    "p99_latency_ms": 210.0,
                    "p50_ttft_ms": 55.0,
                    "p95_ttft_ms": 90.0,
                    "error_rate": 0.1,
                    "error_code_counts": {"rate_limit_exceeded": 1},
                }
            ],
        },
    )
    rows = compare_runs(direct_run, gateway_run)

    report = build_comparison_markdown(
        direct_run=direct_run,
        gateway_run=gateway_run,
        rows=rows,
        generated_at="2026-05-17T00:00:00+00:00",
    )

    assert "# Gateway Overhead Report" in report
    assert "| direct backend | benchmark/results/direct.json |" in report
    assert "| gateway | benchmark/results/gateway.json |" in report
    assert "| 1 | 10.00 | 8.00 | -20.00% | 100.00 | 120.00 | 20.00 |" in report
    assert (
        "150.00 | 180.00 | 30.00 | 190.00 | 210.00 | 20.00 | "
        "40.00 | 55.00 | 15.00 | 60.00 | 90.00 | 30.00 | 10.00 pp | "
        "rate_limit_exceeded: 1"
    ) in report


def test_build_comparison_markdown_renders_prometheus_snapshot() -> None:
    direct_run = BenchmarkRun(
        path=Path("direct.json"),
        payload={
            "base_url": "http://localhost:8000/v1",
            "model": "backend",
            "stream": True,
            "requests_per_level": 10,
            "summaries": [{"concurrency": 1, "rps": 1.0, "error_rate": 0.0}],
        },
    )
    gateway_run = BenchmarkRun(
        path=Path("gateway.json"),
        payload={
            "base_url": "http://localhost:8080/v1",
            "model": "qwen-small",
            "stream": True,
            "requests_per_level": 10,
            "summaries": [{"concurrency": 1, "rps": 1.0, "error_rate": 0.0}],
        },
    )
    snapshot = PrometheusSnapshot(
        path=Path("benchmark/results/prometheus_snapshot_1.json"),
        payload={
            "prometheus_url": "http://localhost:9090",
            "collected_at": "2026-05-19T00:00:00+00:00",
            "queries": {
                "vllm_waiting_requests": {
                    "status": "success",
                    "samples": [
                        {
                            "metric": {"model_name": "qwen", "job": "vllm"},
                            "value": 0.0,
                        }
                    ],
                },
                "vllm_kv_cache_usage_percent": {
                    "status": "success",
                    "samples": [],
                },
            },
        },
    )

    report = build_comparison_markdown(
        direct_run=direct_run,
        gateway_run=gateway_run,
        rows=compare_runs(direct_run, gateway_run),
        generated_at="2026-05-19T00:00:00+00:00",
        prometheus_snapshot=snapshot,
    )

    assert "## Prometheus Snapshot" in report
    assert "| vllm_kv_cache_usage_percent | success | 0 | no samples |" in report
    assert "| vllm_waiting_requests | success | 1 | model_name=qwen, job=vllm: 0.00 |" in report


def test_build_comparison_markdown_renders_prometheus_timeseries_summary() -> None:
    direct_run = BenchmarkRun(
        path=Path("direct.json"),
        payload={
            "base_url": "http://localhost:8000/v1",
            "model": "backend",
            "stream": True,
            "requests_per_level": 10,
            "summaries": [{"concurrency": 1, "rps": 1.0, "error_rate": 0.0}],
        },
    )
    gateway_run = BenchmarkRun(
        path=Path("gateway.json"),
        payload={
            "base_url": "http://localhost:8080/v1",
            "model": "qwen-small",
            "stream": True,
            "requests_per_level": 10,
            "summaries": [{"concurrency": 1, "rps": 1.0, "error_rate": 0.0}],
        },
    )
    timeseries = PrometheusTimeSeries(
        path=Path("benchmark/results/prometheus_timeseries_1.json"),
        payload={
            "prometheus_url": "http://localhost:9090",
            "started_at": "2026-05-19T00:00:00+00:00",
            "ended_at": "2026-05-19T00:01:00+00:00",
            "duration_seconds": 60.0,
            "interval_seconds": 5.0,
            "queries": {
                "vllm_waiting_requests": {
                    "summary": {
                        "point_count": 12,
                        "sample_count": 12,
                        "min": 0.0,
                        "mean": 1.25,
                        "max": 4.0,
                        "last": 0.0,
                    }
                }
            },
        },
    )

    report = build_comparison_markdown(
        direct_run=direct_run,
        gateway_run=gateway_run,
        rows=compare_runs(direct_run, gateway_run),
        generated_at="2026-05-19T00:00:00+00:00",
        prometheus_timeseries=timeseries,
    )

    assert "## Prometheus Time Series Summary" in report
    assert "| vllm_waiting_requests | 12 | 12 | 0.00 | 1.25 | 4.00 | 0.00 |" in report


def test_delta_percent_handles_missing_or_zero_baseline() -> None:
    assert delta_percent(8.0, 10.0) == -0.2
    assert delta_percent(8.0, 0.0) is None
    assert delta_percent(None, 10.0) is None


def test_load_benchmark_run_requires_summaries(tmp_path) -> None:
    result_path = tmp_path / "result.json"
    result_path.write_text('{"base_url":"http://localhost:8080/v1"}', encoding="utf-8")

    with pytest.raises(ValueError, match="missing summaries"):
        load_benchmark_run(result_path)


def test_load_prometheus_snapshot_requires_queries(tmp_path) -> None:
    snapshot_path = tmp_path / "snapshot.json"
    snapshot_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="missing queries"):
        load_prometheus_snapshot(snapshot_path)


def test_load_prometheus_timeseries_requires_queries(tmp_path) -> None:
    timeseries_path = tmp_path / "timeseries.json"
    timeseries_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="missing queries"):
        load_prometheus_timeseries(timeseries_path)
