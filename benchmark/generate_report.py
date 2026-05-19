import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BenchmarkResultFile:
    path: Path
    payload: dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a Markdown benchmark report.")
    parser.add_argument(
        "--results",
        nargs="*",
        help="Benchmark result JSON files or directories. Defaults to benchmark/results.",
    )
    parser.add_argument("--output", default="docs/benchmark_report.md")
    return parser.parse_args()


def resolve_result_paths(inputs: list[str] | None) -> list[Path]:
    if not inputs:
        result_paths = sorted(Path("benchmark/results").glob("benchmark_*.json"))
    else:
        result_paths: list[Path] = []
        for value in inputs:
            path = Path(value)
            if path.is_dir():
                result_paths.extend(sorted(path.glob("benchmark_*.json")))
            else:
                result_paths.append(path)

    if not result_paths:
        raise ValueError("no benchmark result JSON files found")

    missing = [path for path in result_paths if not path.exists()]
    if missing:
        missing_text = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(f"benchmark result file not found: {missing_text}")

    return sorted(result_paths)


def load_benchmark_result(path: Path) -> BenchmarkResultFile:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"benchmark result must be a JSON object: {path}")
    if not isinstance(payload.get("summaries"), list):
        raise ValueError(f"benchmark result missing summaries list: {path}")
    return BenchmarkResultFile(path=path, payload=payload)


def build_markdown_report(
    result_files: list[BenchmarkResultFile],
    generated_at: str,
) -> str:
    lines = [
        "# Benchmark Report",
        "",
        f"Generated at: `{generated_at}`",
        "",
        "## Runs",
        "",
        "| Result File | Base URL | Model | Mode | Requests/Level | Concurrency |",
        "| --- | --- | --- | --- | ---: | --- |",
    ]

    for result_file in result_files:
        payload = result_file.payload
        lines.append(
            markdown_row(
                [
                    display_path(result_file.path),
                    str(payload.get("base_url", "n/a")),
                    str(payload.get("model", "n/a")),
                    format_mode(payload.get("stream")),
                    format_integer(payload.get("requests_per_level")),
                    format_concurrency(payload.get("concurrency")),
                ]
            )
        )

    lines.extend(["", "## Results", ""])

    for result_file in result_files:
        lines.extend(
            [
                f"### `{display_path(result_file.path)}`",
                "",
                "| Concurrency | Total | Success | Errors | RPS | P50 Latency (ms) | "
                "P95 Latency (ms) | P99 Latency (ms) | P50 TTFT (ms) | P95 TTFT (ms) | "
                "P99 TTFT (ms) | P50 ITL (ms) | P95 ITL (ms) | Mean ITL (ms) | "
                "Output Events/s | Output Events | Error Rate | Error Statuses | Error Codes |",
                "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | "
                "---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
            ]
        )
        for summary in result_file.payload["summaries"]:
            if not isinstance(summary, dict):
                continue
            lines.append(markdown_row(summary_cells(summary)))
        lines.append("")

    lines.extend(
        [
            "## Metric Notes",
            "",
            "- E2E latency is measured from request start until the full response completes.",
            "- TTFT is measured until the first non-empty streaming content chunk.",
            "- ITL is the interval between non-empty streaming content chunks.",
            "- Output events count SSE chunks with `delta.content`.",
            "- Output events are not tokenizer-level output token counts.",
            "- Non-streaming runs show `n/a` for TTFT and ITL.",
            "",
        ]
    )
    return "\n".join(lines)


def summary_cells(summary: dict[str, Any]) -> list[str]:
    return [
        format_integer(summary.get("concurrency")),
        format_integer(summary.get("total_requests")),
        format_integer(summary.get("success_count")),
        format_integer(summary.get("error_count")),
        format_float(summary.get("rps")),
        format_float(summary.get("p50_latency_ms")),
        format_float(summary.get("p95_latency_ms")),
        format_float(summary.get("p99_latency_ms")),
        format_float(summary.get("p50_ttft_ms")),
        format_float(summary.get("p95_ttft_ms")),
        format_float(summary.get("p99_ttft_ms")),
        format_float(summary.get("p50_itl_ms")),
        format_float(summary.get("p95_itl_ms")),
        format_float(summary.get("mean_itl_ms")),
        format_float(output_events_per_second(summary)),
        format_integer(summary.get("output_event_count")),
        format_percent(summary.get("error_rate")),
        format_count_map(summary.get("error_status_counts")),
        format_count_map(summary.get("error_code_counts")),
    ]


def output_events_per_second(summary: dict[str, Any]) -> float | None:
    value = summary.get("output_events_per_second")
    if isinstance(value, int | float):
        return float(value)

    output_event_count = summary.get("output_event_count")
    duration_seconds = summary.get("duration_seconds")
    if not isinstance(output_event_count, int):
        return None
    if not isinstance(duration_seconds, int | float) or duration_seconds <= 0:
        return None
    return output_event_count / duration_seconds


def markdown_row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def display_path(path: Path) -> str:
    try:
        path = path.relative_to(Path.cwd())
    except ValueError:
        pass
    return path.as_posix()


def format_mode(stream: Any) -> str:
    if stream is True:
        return "streaming"
    if stream is False:
        return "non-streaming"
    return "n/a"


def format_concurrency(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return "n/a"


def format_integer(value: Any) -> str:
    if isinstance(value, int):
        return str(value)
    return "n/a"


def format_float(value: Any) -> str:
    if isinstance(value, int | float):
        return f"{value:.2f}"
    return "n/a"


def format_percent(value: Any) -> str:
    if isinstance(value, int | float):
        return f"{value * 100:.2f}%"
    return "n/a"


def format_count_map(value: Any) -> str:
    if not isinstance(value, dict) or not value:
        return "none"
    items = [(str(key), item_value) for key, item_value in value.items()]
    return ", ".join(f"{key}: {item_value}" for key, item_value in sorted(items))


def write_report(result_files: list[BenchmarkResultFile], output_path: Path) -> Path:
    generated_at = datetime.now(tz=UTC).isoformat(timespec="seconds")
    report = build_markdown_report(result_files, generated_at=generated_at)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"wrote_report={output_path}")
    return output_path


def main() -> None:
    args = parse_args()
    result_paths = resolve_result_paths(args.results)
    result_files = [load_benchmark_result(path) for path in result_paths]
    write_report(result_files, Path(args.output))


if __name__ == "__main__":
    main()
