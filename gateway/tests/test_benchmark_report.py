from pathlib import Path

import pytest

from benchmark.generate_report import (
    BenchmarkResultFile,
    build_markdown_report,
    load_benchmark_result,
    resolve_result_paths,
)


def test_build_markdown_report_renders_run_summary_and_metrics() -> None:
    result_file = BenchmarkResultFile(
        path=Path("benchmark/results/benchmark_1.json"),
        payload={
            "base_url": "http://127.0.0.1:8080/v1",
            "model": "mock",
            "stream": True,
            "requests_per_level": 3,
            "concurrency": [1],
            "summaries": [
                {
                    "concurrency": 1,
                    "total_requests": 3,
                    "success_count": 3,
                    "error_count": 0,
                    "error_rate": 0.0,
                    "rps": 3.1597,
                    "p50_latency_ms": 277.39,
                    "p95_latency_ms": 383.37,
                    "p99_latency_ms": 401.11,
                    "p50_ttft_ms": 276.41,
                    "p95_ttft_ms": 382.25,
                    "p99_ttft_ms": 398.17,
                    "p50_itl_ms": 0.03,
                    "p95_itl_ms": 0.06,
                    "mean_itl_ms": 0.04,
                    "p50_tpot_ms": 7.5,
                    "p95_tpot_ms": 9.5,
                    "mean_tpot_ms": 8.0,
                    "output_events_per_second": 15.80,
                    "output_event_count": 15,
                    "output_tokens_per_second": 128.5,
                    "output_token_count": 122,
                    "error_status_counts": {},
                    "error_code_counts": {},
                    "duration_seconds": 0.9494,
                }
            ],
        },
    )

    report = build_markdown_report(
        [result_file],
        generated_at="2026-05-17T00:00:00+00:00",
    )

    assert "# Benchmark Report" in report
    assert (
        "| benchmark/results/benchmark_1.json | http://127.0.0.1:8080/v1 | "
        "mock | streaming | 3 | 1 |"
    ) in report
    assert (
        "| 1 | 3 | 3 | 0 | 3.16 | 277.39 | 383.37 | 401.11 | 276.41 | "
        "382.25 | 398.17 | 0.03 | 0.06 | 0.04 | 7.50 | 9.50 | 8.00 | "
        "15.80 | 15 | 128.50 | 122 | 0.00% | none | none |"
    ) in report
    assert "P99 Latency" in report
    assert "P99 TTFT" in report
    assert "P95 ITL" in report
    assert "P95 TPOT" in report
    assert "Output Tokens/s" in report
    assert "Error Codes" in report
    assert "Output events count SSE chunks" in report


def test_resolve_result_paths_accepts_directories_and_sorts_files(tmp_path) -> None:
    result_dir = tmp_path / "results"
    result_dir.mkdir()
    second = result_dir / "benchmark_2.json"
    first = result_dir / "benchmark_1.json"
    other = result_dir / "notes.json"
    second.write_text('{"summaries":[]}', encoding="utf-8")
    first.write_text('{"summaries":[]}', encoding="utf-8")
    other.write_text("{}", encoding="utf-8")

    paths = resolve_result_paths([str(result_dir)])

    assert paths == [first, second]


def test_load_benchmark_result_requires_object_with_summaries(tmp_path) -> None:
    result_path = tmp_path / "benchmark_1.json"
    result_path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="must be a JSON object"):
        load_benchmark_result(result_path)
