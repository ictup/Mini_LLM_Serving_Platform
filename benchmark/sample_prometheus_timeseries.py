import argparse
import json
import math
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

try:
    from benchmark.collect_prometheus_snapshot import PROMETHEUS_QUERIES, query_prometheus
except ModuleNotFoundError:
    from collect_prometheus_snapshot import PROMETHEUS_QUERIES, query_prometheus


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sample Prometheus metrics over time.")
    parser.add_argument("--prometheus-url", default="http://localhost:9090")
    parser.add_argument("--duration-seconds", type=float, default=300)
    parser.add_argument("--interval-seconds", type=float, default=5)
    parser.add_argument("--output-dir", default="benchmark/results")
    parser.add_argument("--timeout-seconds", type=float, default=10)
    args = parser.parse_args()
    validate_args(args)
    return args


def validate_args(args: argparse.Namespace) -> None:
    if args.duration_seconds <= 0:
        raise ValueError("--duration-seconds must be positive")
    if args.interval_seconds <= 0:
        raise ValueError("--interval-seconds must be positive")
    if args.timeout_seconds <= 0:
        raise ValueError("--timeout-seconds must be positive")


def sample_prometheus_timeseries(
    *,
    prometheus_url: str,
    duration_seconds: float,
    interval_seconds: float,
    timeout_seconds: float,
    queries: dict[str, str] = PROMETHEUS_QUERIES,
) -> dict[str, Any]:
    started_monotonic = time.monotonic()
    deadline = started_monotonic + duration_seconds
    started_at = datetime.now(tz=UTC).isoformat(timespec="seconds")
    query_results: dict[str, dict[str, Any]] = {
        name: {"query": query, "points": []} for name, query in queries.items()
    }

    with httpx.Client(timeout=timeout_seconds) as client:
        while True:
            collected_at = datetime.now(tz=UTC).isoformat(timespec="seconds")
            collected_at_unix = time.time()
            for name, query in queries.items():
                point = sample_query(
                    client=client,
                    prometheus_url=prometheus_url,
                    query=query,
                    collected_at=collected_at,
                    collected_at_unix=collected_at_unix,
                )
                query_results[name]["points"].append(point)

            if time.monotonic() >= deadline:
                break
            sleep_seconds = min(interval_seconds, max(0.0, deadline - time.monotonic()))
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)

    ended_at = datetime.now(tz=UTC).isoformat(timespec="seconds")
    for result in query_results.values():
        result["summary"] = summarize_points(result["points"])

    return {
        "schema_version": 1,
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_seconds": round(time.monotonic() - started_monotonic, 3),
        "interval_seconds": interval_seconds,
        "prometheus_url": prometheus_url,
        "queries": query_results,
    }


def sample_query(
    *,
    client: httpx.Client,
    prometheus_url: str,
    query: str,
    collected_at: str,
    collected_at_unix: float,
) -> dict[str, Any]:
    try:
        result = query_prometheus(client, prometheus_url=prometheus_url, query=query)
    except Exception as exc:
        result = {
            "status": "error",
            "result_type": "unknown",
            "samples": [],
            "error": type(exc).__name__,
        }

    return {
        "collected_at": collected_at,
        "collected_at_unix": round(collected_at_unix, 3),
        "status": result.get("status", "unknown"),
        "samples": result.get("samples", []),
        "error": result.get("error"),
    }


def summarize_points(points: list[dict[str, Any]]) -> dict[str, Any]:
    values = [
        value
        for point in points
        for value in sample_values(point.get("samples"))
        if math.isfinite(value)
    ]

    if not values:
        return {
            "sample_count": 0,
            "point_count": len(points),
            "min": None,
            "mean": None,
            "max": None,
            "last": None,
        }

    return {
        "sample_count": len(values),
        "point_count": len(points),
        "min": round(min(values), 6),
        "mean": round(sum(values) / len(values), 6),
        "max": round(max(values), 6),
        "last": round(values[-1], 6),
    }


def sample_values(samples: Any) -> list[float]:
    if not isinstance(samples, list):
        return []

    values: list[float] = []
    for sample in samples:
        if not isinstance(sample, dict):
            continue
        value = sample.get("value")
        if isinstance(value, int | float):
            values.append(float(value))
    return values


def write_timeseries(timeseries: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"prometheus_timeseries_{int(time.time())}.json"
    output_path.write_text(json.dumps(timeseries, indent=2), encoding="utf-8")
    print(f"wrote_timeseries={output_path}")
    return output_path


def print_timeseries_summary(timeseries: dict[str, Any]) -> None:
    queries = timeseries.get("queries", {})
    if not isinstance(queries, dict):
        return

    for name, result in queries.items():
        if not isinstance(result, dict):
            continue
        summary = result.get("summary")
        if not isinstance(summary, dict):
            continue
        print(
            f"{name}: points={summary.get('point_count', 0)} "
            f"samples={summary.get('sample_count', 0)} "
            f"max={format_summary_value(summary.get('max'))}"
        )


def format_summary_value(value: Any) -> str:
    if isinstance(value, int | float):
        return f"{value:.4f}"
    return "n/a"


def main() -> None:
    args = parse_args()
    timeseries = sample_prometheus_timeseries(
        prometheus_url=args.prometheus_url,
        duration_seconds=args.duration_seconds,
        interval_seconds=args.interval_seconds,
        timeout_seconds=args.timeout_seconds,
    )
    print_timeseries_summary(timeseries)
    write_timeseries(timeseries, Path(args.output_dir))


if __name__ == "__main__":
    main()
