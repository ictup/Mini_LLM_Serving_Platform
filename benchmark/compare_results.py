import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BenchmarkRun:
    path: Path
    payload: dict[str, Any]


@dataclass(frozen=True)
class PrometheusSnapshot:
    path: Path
    payload: dict[str, Any]


@dataclass(frozen=True)
class ComparisonRow:
    concurrency: int
    direct_summary: dict[str, Any]
    gateway_summary: dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare direct backend and Gateway benchmarks.")
    parser.add_argument("--direct-result", required=True)
    parser.add_argument("--gateway-result", required=True)
    parser.add_argument("--prometheus-snapshot")
    parser.add_argument("--output", default="docs/gateway_overhead_report.md")
    return parser.parse_args()


def load_benchmark_run(path: Path) -> BenchmarkRun:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"benchmark result must be a JSON object: {path}")
    if not isinstance(payload.get("summaries"), list):
        raise ValueError(f"benchmark result missing summaries list: {path}")
    return BenchmarkRun(path=path, payload=payload)


def load_prometheus_snapshot(path: Path) -> PrometheusSnapshot:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Prometheus snapshot must be a JSON object: {path}")
    if not isinstance(payload.get("queries"), dict):
        raise ValueError(f"Prometheus snapshot missing queries object: {path}")
    return PrometheusSnapshot(path=path, payload=payload)


def compare_runs(direct_run: BenchmarkRun, gateway_run: BenchmarkRun) -> list[ComparisonRow]:
    direct_by_concurrency = summaries_by_concurrency(direct_run)
    gateway_by_concurrency = summaries_by_concurrency(gateway_run)
    common_concurrency = sorted(direct_by_concurrency.keys() & gateway_by_concurrency.keys())

    if not common_concurrency:
        raise ValueError("direct and Gateway benchmark results have no shared concurrency levels")

    return [
        ComparisonRow(
            concurrency=concurrency,
            direct_summary=direct_by_concurrency[concurrency],
            gateway_summary=gateway_by_concurrency[concurrency],
        )
        for concurrency in common_concurrency
    ]


def summaries_by_concurrency(run: BenchmarkRun) -> dict[int, dict[str, Any]]:
    summaries: dict[int, dict[str, Any]] = {}
    for summary in run.payload["summaries"]:
        if not isinstance(summary, dict):
            continue
        concurrency = summary.get("concurrency")
        if isinstance(concurrency, int):
            summaries[concurrency] = summary
    return summaries


def build_comparison_markdown(
    direct_run: BenchmarkRun,
    gateway_run: BenchmarkRun,
    rows: list[ComparisonRow],
    generated_at: str,
    prometheus_snapshot: PrometheusSnapshot | None = None,
) -> str:
    lines = [
        "# Gateway Overhead Report",
        "",
        f"Generated at: `{generated_at}`",
        "",
        "## Inputs",
        "",
        "| Path | Result File | Base URL | Model | Mode | Requests/Level |",
        "| --- | --- | --- | --- | --- | ---: |",
        run_row("direct backend", direct_run),
        run_row("gateway", gateway_run),
        "",
        "## Direct Backend vs Gateway",
        "",
        "| Concurrency | Direct RPS | Gateway RPS | RPS Delta | Direct P50 Latency (ms) | "
        "Gateway P50 Latency (ms) | P50 Overhead (ms) | Direct P95 Latency (ms) | "
        "Gateway P95 Latency (ms) | P95 Overhead (ms) | Direct P99 Latency (ms) | "
        "Gateway P99 Latency (ms) | P99 Overhead (ms) | Direct P50 TTFT (ms) | "
        "Gateway P50 TTFT (ms) | P50 TTFT Overhead (ms) | Direct P95 TTFT (ms) | "
        "Gateway P95 TTFT (ms) | P95 TTFT Overhead (ms) | Error Delta | "
        "Gateway Error Codes |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | "
        "---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]

    for row in rows:
        lines.append(comparison_row(row))

    if prometheus_snapshot is not None:
        lines.extend(prometheus_snapshot_section(prometheus_snapshot))

    lines.extend(
        [
            "",
            "## Metric Notes",
            "",
            "- Positive latency overhead means Gateway is slower than the direct backend path.",
            "- Negative RPS delta means Gateway achieved lower throughput than direct backend.",
            "- Negative latency overhead can happen in local sequential runs due to run-to-run "
            "variance, warmup state, output length variance, and vLLM scheduling. It should be "
            "interpreted as no obvious Gateway bottleneck, not as proof that Gateway accelerates "
            "the backend.",
            "- Compare runs only when prompts, stream mode, max tokens, and concurrency match.",
            "- Output event counts are SSE chunks, not tokenizer-level output token counts.",
            "",
        ]
    )
    return "\n".join(lines)


def prometheus_snapshot_section(snapshot: PrometheusSnapshot) -> list[str]:
    payload = snapshot.payload
    lines = [
        "",
        "## Prometheus Snapshot",
        "",
        "| Snapshot File | Prometheus URL | Collected At |",
        "| --- | --- | --- |",
        markdown_row(
            [
                display_path(snapshot.path),
                str(payload.get("prometheus_url", "n/a")),
                str(payload.get("collected_at", "n/a")),
            ]
        ),
        "",
        "| Metric | Status | Samples | Values |",
        "| --- | --- | ---: | --- |",
    ]

    queries = payload.get("queries", {})
    if isinstance(queries, dict):
        for metric_name in sorted(queries):
            result = queries[metric_name]
            if isinstance(result, dict):
                lines.append(prometheus_metric_row(metric_name, result))

    lines.extend(
        [
            "",
            "Prometheus snapshot values are point-in-time query results collected after the "
            "benchmark run. Empty samples usually mean the metric was absent, had no data in "
            "the query window, or is not exposed by the current backend/version.",
        ]
    )
    return lines


def prometheus_metric_row(metric_name: str, result: dict[str, Any]) -> str:
    samples = result.get("samples")
    sample_count = len(samples) if isinstance(samples, list) else 0
    return markdown_row(
        [
            metric_name,
            str(result.get("status", "unknown")),
            str(sample_count),
            format_prometheus_samples(samples),
        ]
    )


def format_prometheus_samples(samples: Any) -> str:
    if not isinstance(samples, list) or not samples:
        return "no samples"

    formatted_samples = [
        format_prometheus_sample(sample)
        for sample in samples
        if isinstance(sample, dict)
    ]
    if not formatted_samples:
        return "no samples"
    return "<br>".join(formatted_samples)


def format_prometheus_sample(sample: dict[str, Any]) -> str:
    value = sample.get("value")
    metric = sample.get("metric")
    labels = format_prometheus_labels(metric)
    formatted_value = format_float(value)
    if labels == "none":
        return formatted_value
    return f"{labels}: {formatted_value}"


def format_prometheus_labels(metric: Any) -> str:
    if not isinstance(metric, dict):
        return "none"

    label_keys = ("model", "backend_model", "model_name", "job", "instance")
    labels = [
        f"{key}={metric[key]}"
        for key in label_keys
        if isinstance(metric.get(key), str)
    ]
    if not labels:
        return "none"
    return ", ".join(labels)


def run_row(label: str, run: BenchmarkRun) -> str:
    payload = run.payload
    return markdown_row(
        [
            label,
            display_path(run.path),
            str(payload.get("base_url", "n/a")),
            str(payload.get("model", "n/a")),
            format_mode(payload.get("stream")),
            format_integer(payload.get("requests_per_level")),
        ]
    )


def comparison_row(row: ComparisonRow) -> str:
    direct = row.direct_summary
    gateway = row.gateway_summary
    return markdown_row(
        [
            str(row.concurrency),
            format_float(direct.get("rps")),
            format_float(gateway.get("rps")),
            format_percent(delta_percent(gateway.get("rps"), direct.get("rps"))),
            format_float(direct.get("p50_latency_ms")),
            format_float(gateway.get("p50_latency_ms")),
            format_float(delta(gateway.get("p50_latency_ms"), direct.get("p50_latency_ms"))),
            format_float(direct.get("p95_latency_ms")),
            format_float(gateway.get("p95_latency_ms")),
            format_float(delta(gateway.get("p95_latency_ms"), direct.get("p95_latency_ms"))),
            format_float(direct.get("p99_latency_ms")),
            format_float(gateway.get("p99_latency_ms")),
            format_float(delta(gateway.get("p99_latency_ms"), direct.get("p99_latency_ms"))),
            format_float(direct.get("p50_ttft_ms")),
            format_float(gateway.get("p50_ttft_ms")),
            format_float(delta(gateway.get("p50_ttft_ms"), direct.get("p50_ttft_ms"))),
            format_float(direct.get("p95_ttft_ms")),
            format_float(gateway.get("p95_ttft_ms")),
            format_float(delta(gateway.get("p95_ttft_ms"), direct.get("p95_ttft_ms"))),
            format_percentage_points(delta(gateway.get("error_rate"), direct.get("error_rate"))),
            format_count_map(gateway.get("error_code_counts")),
        ]
    )


def delta(left: Any, right: Any) -> float | None:
    if isinstance(left, int | float) and isinstance(right, int | float):
        return left - right
    return None


def delta_percent(value: Any, baseline: Any) -> float | None:
    if not isinstance(value, int | float) or not isinstance(baseline, int | float):
        return None
    if baseline == 0:
        return None
    return (value - baseline) / baseline


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


def format_percentage_points(value: Any) -> str:
    if isinstance(value, int | float):
        return f"{value * 100:.2f} pp"
    return "n/a"


def format_count_map(value: Any) -> str:
    if not isinstance(value, dict) or not value:
        return "none"
    items = [(str(key), item_value) for key, item_value in value.items()]
    return ", ".join(f"{key}: {item_value}" for key, item_value in sorted(items))


def write_comparison_report(
    direct_run: BenchmarkRun,
    gateway_run: BenchmarkRun,
    output_path: Path,
    prometheus_snapshot: PrometheusSnapshot | None = None,
) -> Path:
    rows = compare_runs(direct_run, gateway_run)
    generated_at = datetime.now(tz=UTC).isoformat(timespec="seconds")
    report = build_comparison_markdown(
        direct_run=direct_run,
        gateway_run=gateway_run,
        rows=rows,
        generated_at=generated_at,
        prometheus_snapshot=prometheus_snapshot,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"wrote_report={output_path}")
    return output_path


def main() -> None:
    args = parse_args()
    direct_run = load_benchmark_run(Path(args.direct_result))
    gateway_run = load_benchmark_run(Path(args.gateway_result))
    prometheus_snapshot = (
        load_prometheus_snapshot(Path(args.prometheus_snapshot))
        if args.prometheus_snapshot
        else None
    )
    write_comparison_report(
        direct_run,
        gateway_run,
        Path(args.output),
        prometheus_snapshot=prometheus_snapshot,
    )


if __name__ == "__main__":
    main()
