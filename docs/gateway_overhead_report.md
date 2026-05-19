# Gateway Overhead Report

Generated at: `2026-05-19T20:37:28+00:00`

## Inputs

| Path | Result File | Base URL | Model | Mode | Requests/Level |
| --- | --- | --- | --- | --- | ---: |
| direct backend | benchmark/results/benchmark_1779222497.json | http://localhost:8000/v1 | Qwen/Qwen2.5-0.5B-Instruct | streaming | 100 |
| gateway | benchmark/results/benchmark_1779222956.json | http://localhost:8080/v1 | qwen-small | streaming | 100 |

## Direct Backend vs Gateway

| Concurrency | Direct RPS | Gateway RPS | RPS Delta | Direct P50 Latency (ms) | Gateway P50 Latency (ms) | P50 Overhead (ms) | Direct P95 Latency (ms) | Gateway P95 Latency (ms) | P95 Overhead (ms) | Direct P99 Latency (ms) | Gateway P99 Latency (ms) | P99 Overhead (ms) | Direct P50 TTFT (ms) | Gateway P50 TTFT (ms) | P50 TTFT Overhead (ms) | Direct P95 TTFT (ms) | Gateway P95 TTFT (ms) | P95 TTFT Overhead (ms) | Error Delta | Gateway Error Codes |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 1.73 | 1.85 | 7.06% | 369.68 | 334.78 | -34.90 | 1043.08 | 1047.83 | 4.75 | 1079.73 | 1062.95 | -16.78 | 31.16 | 42.54 | 11.38 | 44.47 | 52.93 | 8.46 | 0.00 pp | none |
| 4 | 5.71 | 5.38 | -5.79% | 464.32 | 468.48 | 4.16 | 1256.95 | 1278.05 | 21.10 | 1279.68 | 1297.34 | 17.66 | 42.89 | 54.69 | 11.80 | 57.51 | 82.13 | 24.62 | 0.00 pp | none |
| 8 | 9.45 | 9.08 | -3.97% | 507.77 | 515.74 | 7.97 | 1474.63 | 1551.73 | 77.10 | 1489.29 | 1563.41 | 74.12 | 45.35 | 57.66 | 12.31 | 98.91 | 161.24 | 62.33 | 0.00 pp | none |
| 16 | 13.58 | 12.56 | -7.55% | 693.88 | 809.08 | 115.20 | 2004.51 | 2232.31 | 227.80 | 2034.30 | 2320.18 | 285.88 | 49.89 | 77.95 | 28.06 | 134.05 | 242.43 | 108.38 | 0.00 pp | none |
| 32 | 17.87 | 15.94 | -10.80% | 1101.15 | 1350.35 | 249.20 | 3121.88 | 3567.71 | 445.83 | 3124.27 | 3568.78 | 444.51 | 67.98 | 124.27 | 56.29 | 268.89 | 477.44 | 208.55 | 0.00 pp | none |

## Prometheus Snapshot

| Snapshot File | Prometheus URL | Collected At |
| --- | --- | --- |
| benchmark/results/prometheus_snapshot_1779223042.json | http://localhost:9090 | 2026-05-19T20:37:22+00:00 |

| Metric | Status | Samples | Values |
| --- | --- | ---: | --- |
| gateway_error_rate_rps | success | 0 | no samples |
| gateway_output_chunks_per_second | success | 1 | model=qwen-small, backend_model=Qwen/Qwen2.5-0.5B-Instruct: 0.00 |
| gateway_p95_latency_seconds | success | 1 | 0.30 |
| gateway_p95_ttft_seconds | success | 1 | model=qwen-small, backend_model=Qwen/Qwen2.5-0.5B-Instruct: 0.09 |
| gateway_request_rate_rps | success | 1 | 0.28 |
| vllm_generation_tokens_per_second | success | 1 | model_name=Qwen/Qwen2.5-0.5B-Instruct: 0.00 |
| vllm_kv_cache_usage_percent | success | 1 | model_name=Qwen/Qwen2.5-0.5B-Instruct, job=vllm, instance=vllm:8000: 0.00 |
| vllm_p95_e2e_latency_seconds | success | 1 | model_name=Qwen/Qwen2.5-0.5B-Instruct: 3.41 |
| vllm_p95_inter_token_latency_seconds | success | 0 | no samples |
| vllm_p95_ttft_seconds | success | 1 | model_name=Qwen/Qwen2.5-0.5B-Instruct: 0.08 |
| vllm_prompt_tokens_per_second | success | 1 | model_name=Qwen/Qwen2.5-0.5B-Instruct: 0.00 |
| vllm_running_requests | success | 1 | model_name=Qwen/Qwen2.5-0.5B-Instruct, job=vllm, instance=vllm:8000: 0.00 |
| vllm_waiting_requests | success | 1 | model_name=Qwen/Qwen2.5-0.5B-Instruct, job=vllm, instance=vllm:8000: 0.00 |

Prometheus snapshot values are point-in-time query results collected after the benchmark run. Empty samples usually mean the metric was absent, had no data in the query window, or is not exposed by the current backend/version.

## Prometheus Time Series Summary

| Time Series File | Prometheus URL | Started At | Ended At | Duration (s) | Interval (s) |
| --- | --- | --- | --- | ---: | ---: |
| benchmark/results/prometheus_timeseries_1779223033.json | http://localhost:9090 | 2026-05-19T20:34:13+00:00 | 2026-05-19T20:37:13+00:00 | 180.01 | 5.00 |

| Metric | Points | Samples | Min | Mean | Max | Last |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| gateway_error_rate_rps | 37 | 0 | n/a | n/a | n/a | n/a |
| gateway_output_chunks_per_second | 37 | 37 | 0.00 | 197.15 | 566.63 | 0.00 |
| gateway_p95_latency_seconds | 37 | 37 | 0.01 | 0.16 | 0.30 | 0.30 |
| gateway_p95_ttft_seconds | 37 | 36 | 0.04 | 0.07 | 0.22 | 0.09 |
| gateway_request_rate_rps | 37 | 37 | 0.25 | 3.07 | 8.26 | 0.25 |
| vllm_generation_tokens_per_second | 37 | 37 | 0.00 | 190.74 | 527.53 | 0.00 |
| vllm_kv_cache_usage_percent | 37 | 37 | 0.00 | 0.07 | 0.75 | 0.00 |
| vllm_p95_e2e_latency_seconds | 37 | 36 | 0.75 | 2.12 | 3.41 | 3.41 |
| vllm_p95_inter_token_latency_seconds | 37 | 0 | n/a | n/a | n/a | n/a |
| vllm_p95_ttft_seconds | 37 | 36 | 0.04 | 0.06 | 0.19 | 0.08 |
| vllm_prompt_tokens_per_second | 37 | 37 | 0.00 | 104.06 | 292.56 | 0.00 |
| vllm_running_requests | 37 | 37 | 0.00 | 2.22 | 22.00 | 0.00 |
| vllm_waiting_requests | 37 | 37 | 0.00 | 0.00 | 0.00 | 0.00 |

Prometheus time-series values are sampled while the benchmark is running. For gauges, max highlights peak pressure. For rate and histogram queries, mean/max summarize the query output over the sampling window.

## Metric Notes

- Positive latency overhead means Gateway is slower than the direct backend path.
- Negative RPS delta means Gateway achieved lower throughput than direct backend.
- Negative latency overhead can happen in local sequential runs due to run-to-run variance, warmup state, output length variance, and vLLM scheduling. It should be interpreted as no obvious Gateway bottleneck, not as proof that Gateway accelerates the backend.
- Compare runs only when prompts, stream mode, max tokens, and concurrency match.
- Output event counts are SSE chunks, not tokenizer-level output token counts.
