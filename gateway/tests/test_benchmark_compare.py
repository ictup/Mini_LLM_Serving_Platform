from pathlib import Path

import pytest

from benchmark.compare_results import (
    BenchmarkRun,
    build_comparison_markdown,
    compare_runs,
    delta_percent,
    load_benchmark_run,
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
        "40.00 | 55.00 | 15.00 | 60.00 | 90.00 | 30.00 | 10.00 pp"
    ) in report


def test_delta_percent_handles_missing_or_zero_baseline() -> None:
    assert delta_percent(8.0, 10.0) == -0.2
    assert delta_percent(8.0, 0.0) is None
    assert delta_percent(None, 10.0) is None


def test_load_benchmark_run_requires_summaries(tmp_path) -> None:
    result_path = tmp_path / "result.json"
    result_path.write_text('{"base_url":"http://localhost:8080/v1"}', encoding="utf-8")

    with pytest.raises(ValueError, match="missing summaries"):
        load_benchmark_run(result_path)
