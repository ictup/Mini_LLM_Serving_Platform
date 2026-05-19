import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

PROMETHEUS_QUERIES: dict[str, str] = {
    "gateway_request_rate_rps": "sum(rate(gateway_http_requests_total[1m]))",
    "gateway_error_rate_rps": "sum(rate(gateway_http_errors_total[1m]))",
    "gateway_p95_latency_seconds": (
        "histogram_quantile(0.95, "
        "sum(rate(gateway_http_request_duration_seconds_bucket[5m])) by (le))"
    ),
    "gateway_p95_ttft_seconds": (
        "histogram_quantile(0.95, "
        "sum(rate(gateway_stream_ttft_seconds_bucket[5m])) by (le, model, backend_model))"
    ),
    "gateway_output_chunks_per_second": (
        "sum by (model, backend_model) (rate(gateway_stream_output_chunks_total[1m]))"
    ),
    "vllm_running_requests": "vllm:num_requests_running",
    "vllm_waiting_requests": "vllm:num_requests_waiting",
    "vllm_kv_cache_usage_percent": (
        "(vllm:kv_cache_usage_perc or vllm:gpu_cache_usage_perc) * 100"
    ),
    "vllm_prompt_tokens_per_second": "sum by (model_name) (rate(vllm:prompt_tokens_total[1m]))",
    "vllm_generation_tokens_per_second": (
        "sum by (model_name) (rate(vllm:generation_tokens_total[1m]))"
    ),
    "vllm_p95_ttft_seconds": (
        "histogram_quantile(0.95, "
        "sum(rate(vllm:time_to_first_token_seconds_bucket[5m])) by (le, model_name))"
    ),
    "vllm_p95_e2e_latency_seconds": (
        "histogram_quantile(0.95, "
        "sum(rate(vllm:e2e_request_latency_seconds_bucket[5m])) by (le, model_name))"
    ),
    "vllm_p95_inter_token_latency_seconds": (
        "histogram_quantile(0.95, "
        "sum(rate(vllm:inter_token_latency_seconds_bucket[5m])) by (le, model_name))"
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect a Prometheus metrics snapshot.")
    parser.add_argument("--prometheus-url", default="http://localhost:9090")
    parser.add_argument("--output-dir", default="benchmark/results")
    parser.add_argument("--timeout-seconds", type=float, default=10)
    return parser.parse_args()


def query_prometheus(
    client: httpx.Client,
    prometheus_url: str,
    query: str,
) -> dict[str, Any]:
    response = client.get(
        f"{prometheus_url.rstrip('/')}/api/v1/query",
        params={"query": query},
    )
    response.raise_for_status()
    return normalize_query_response(response.json())


def normalize_query_response(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("status") != "success":
        return {
            "status": str(payload.get("status", "error")),
            "result_type": "unknown",
            "samples": [],
            "error": str(payload.get("error", "prometheus query failed")),
        }

    data = payload.get("data")
    if not isinstance(data, dict):
        return {
            "status": "error",
            "result_type": "unknown",
            "samples": [],
            "error": "prometheus response missing data object",
        }

    result = data.get("result")
    if not isinstance(result, list):
        return {
            "status": "error",
            "result_type": str(data.get("resultType", "unknown")),
            "samples": [],
            "error": "prometheus response missing result list",
        }

    return {
        "status": "success",
        "result_type": str(data.get("resultType", "unknown")),
        "samples": [normalize_sample(sample) for sample in result if isinstance(sample, dict)],
    }


def normalize_sample(sample: dict[str, Any]) -> dict[str, Any]:
    metric = sample.get("metric")
    value = sample.get("value")
    return {
        "metric": metric if isinstance(metric, dict) else {},
        "timestamp": value[0] if isinstance(value, list) and len(value) >= 2 else None,
        "value": parse_prometheus_value(value),
    }


def parse_prometheus_value(value: Any) -> float | None:
    if not isinstance(value, list) or len(value) < 2:
        return None
    raw_value = value[1]
    if not isinstance(raw_value, str):
        return None
    try:
        return float(raw_value)
    except ValueError:
        return None


def collect_snapshot(
    prometheus_url: str,
    timeout_seconds: float,
    queries: dict[str, str] = PROMETHEUS_QUERIES,
) -> dict[str, Any]:
    collected_at = datetime.now(tz=UTC).isoformat(timespec="seconds")
    snapshot: dict[str, Any] = {
        "schema_version": 1,
        "collected_at": collected_at,
        "prometheus_url": prometheus_url,
        "queries": {},
    }

    with httpx.Client(timeout=timeout_seconds) as client:
        for name, query in queries.items():
            try:
                result = query_prometheus(client, prometheus_url=prometheus_url, query=query)
            except Exception as exc:
                result = {
                    "status": "error",
                    "result_type": "unknown",
                    "samples": [],
                    "error": type(exc).__name__,
                }
            result["query"] = query
            snapshot["queries"][name] = result

    return snapshot


def write_snapshot(snapshot: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"prometheus_snapshot_{int(time.time())}.json"
    output_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    print(f"wrote_snapshot={output_path}")
    return output_path


def print_snapshot_summary(snapshot: dict[str, Any]) -> None:
    queries = snapshot.get("queries", {})
    if not isinstance(queries, dict):
        return

    for name, result in queries.items():
        if not isinstance(result, dict):
            continue
        status = result.get("status", "unknown")
        samples = result.get("samples", [])
        sample_count = len(samples) if isinstance(samples, list) else 0
        print(f"{name}: status={status} samples={sample_count}")


def main() -> None:
    args = parse_args()
    snapshot = collect_snapshot(
        prometheus_url=args.prometheus_url,
        timeout_seconds=args.timeout_seconds,
    )
    print_snapshot_summary(snapshot)
    write_snapshot(snapshot, Path(args.output_dir))


if __name__ == "__main__":
    main()
