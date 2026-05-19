# Gateway Overhead Report

Generated at: `2026-05-19T20:28:31+00:00`

## Inputs

| Path | Result File | Base URL | Model | Mode | Requests/Level |
| --- | --- | --- | --- | --- | ---: |
| direct backend | benchmark/results/benchmark_1779222497.json | http://localhost:8000/v1 | Qwen/Qwen2.5-0.5B-Instruct | streaming | 100 |
| gateway | benchmark/results/benchmark_1779222193.json | http://localhost:8080/v1 | qwen-small | streaming | 100 |

## Direct Backend vs Gateway

| Concurrency | Direct RPS | Gateway RPS | RPS Delta | Direct P50 Latency (ms) | Gateway P50 Latency (ms) | P50 Overhead (ms) | Direct P95 Latency (ms) | Gateway P95 Latency (ms) | P95 Overhead (ms) | Direct P99 Latency (ms) | Gateway P99 Latency (ms) | P99 Overhead (ms) | Direct P50 TTFT (ms) | Gateway P50 TTFT (ms) | P50 TTFT Overhead (ms) | Direct P95 TTFT (ms) | Gateway P95 TTFT (ms) | P95 TTFT Overhead (ms) | Error Delta | Gateway Error Codes |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 1.73 | 1.79 | 3.93% | 369.68 | 356.18 | -13.50 | 1043.08 | 1043.26 | 0.18 | 1079.73 | 1072.58 | -7.15 | 31.16 | 44.38 | 13.22 | 44.47 | 56.59 | 12.12 | 0.00 pp | none |
| 4 | 5.71 | 6.33 | 10.93% | 464.32 | 382.66 | -81.66 | 1256.95 | 1113.98 | -142.97 | 1279.68 | 1136.91 | -142.77 | 42.89 | 52.30 | 9.41 | 57.51 | 75.01 | 17.50 | 0.00 pp | none |
| 8 | 9.45 | 10.27 | 8.64% | 507.77 | 480.61 | -27.16 | 1474.63 | 1335.13 | -139.50 | 1489.29 | 1378.17 | -111.12 | 45.35 | 56.93 | 11.58 | 98.91 | 153.49 | 54.58 | 0.00 pp | none |
| 16 | 13.58 | 14.06 | 3.49% | 693.88 | 633.53 | -60.35 | 2004.51 | 1984.73 | -19.78 | 2034.30 | 1999.47 | -34.83 | 49.89 | 75.39 | 25.50 | 134.05 | 234.04 | 99.99 | 0.00 pp | none |
| 32 | 17.87 | 17.84 | -0.19% | 1101.15 | 1185.10 | 83.95 | 3121.88 | 3205.48 | 83.60 | 3124.27 | 3207.45 | 83.18 | 67.98 | 132.23 | 64.25 | 268.89 | 453.89 | 185.00 | 0.00 pp | none |

## Prometheus Snapshot

| Snapshot File | Prometheus URL | Collected At |
| --- | --- | --- |
| benchmark/results/prometheus_snapshot_1779222331.json | http://localhost:9090 | 2026-05-19T20:25:30+00:00 |

| Metric | Status | Samples | Values |
| --- | --- | ---: | --- |
| gateway_error_rate_rps | success | 0 | no samples |
| gateway_output_chunks_per_second | success | 1 | model=qwen-small, backend_model=Qwen/Qwen2.5-0.5B-Instruct: 0.00 |
| gateway_p95_latency_seconds | success | 1 | 0.26 |
| gateway_p95_ttft_seconds | success | 1 | model=qwen-small, backend_model=Qwen/Qwen2.5-0.5B-Instruct: 0.08 |
| gateway_request_rate_rps | success | 1 | 0.26 |
| vllm_generation_tokens_per_second | success | 1 | model_name=Qwen/Qwen2.5-0.5B-Instruct: 0.00 |
| vllm_kv_cache_usage_percent | success | 0 | no samples |
| vllm_p95_e2e_latency_seconds | success | 1 | model_name=Qwen/Qwen2.5-0.5B-Instruct: 4.03 |
| vllm_p95_inter_token_latency_seconds | success | 0 | no samples |
| vllm_p95_ttft_seconds | success | 1 | model_name=Qwen/Qwen2.5-0.5B-Instruct: 0.07 |
| vllm_prompt_tokens_per_second | success | 1 | model_name=Qwen/Qwen2.5-0.5B-Instruct: 0.00 |
| vllm_running_requests | success | 1 | model_name=Qwen/Qwen2.5-0.5B-Instruct, job=vllm, instance=vllm:8000: 0.00 |
| vllm_waiting_requests | success | 1 | model_name=Qwen/Qwen2.5-0.5B-Instruct, job=vllm, instance=vllm:8000: 0.00 |

Prometheus snapshot values are point-in-time query results collected after the benchmark run. Empty samples usually mean the metric was absent, had no data in the query window, or is not exposed by the current backend/version.

## Prometheus Time Series Summary

| Time Series File | Prometheus URL | Started At | Ended At | Duration (s) | Interval (s) |
| --- | --- | --- | --- | ---: | ---: |
| benchmark/results/prometheus_timeseries_1779222273.json | http://localhost:9090 | 2026-05-19T20:21:33+00:00 | 2026-05-19T20:24:33+00:00 | 180.01 | 5.00 |

| Metric | Points | Samples | Min | Mean | Max | Last |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| gateway_error_rate_rps | 37 | 0 | n/a | n/a | n/a | n/a |
| gateway_output_chunks_per_second | 37 | 37 | 0.00 | 185.44 | 537.82 | 0.00 |
| gateway_p95_latency_seconds | 37 | 37 | 0.01 | 0.14 | 0.28 | 0.26 |
| gateway_p95_ttft_seconds | 37 | 36 | 0.04 | 0.07 | 0.21 | 0.08 |
| gateway_request_rate_rps | 37 | 37 | 0.27 | 2.92 | 7.93 | 0.27 |
| vllm_generation_tokens_per_second | 37 | 37 | 0.00 | 192.10 | 537.83 | 0.00 |
| vllm_kv_cache_usage_percent | 37 | 0 | n/a | n/a | n/a | n/a |
| vllm_p95_e2e_latency_seconds | 37 | 35 | 0.96 | 2.43 | 4.03 | 4.03 |
| vllm_p95_inter_token_latency_seconds | 37 | 0 | n/a | n/a | n/a | n/a |
| vllm_p95_ttft_seconds | 37 | 35 | 0.03 | 0.06 | 0.18 | 0.07 |
| vllm_prompt_tokens_per_second | 37 | 37 | 0.00 | 105.59 | 297.28 | 0.00 |
| vllm_running_requests | 37 | 37 | 0.00 | 1.78 | 20.00 | 0.00 |
| vllm_waiting_requests | 37 | 37 | 0.00 | 0.00 | 0.00 | 0.00 |

Prometheus time-series values are sampled while the benchmark is running. For gauges, max highlights peak pressure. For rate and histogram queries, mean/max summarize the query output over the sampling window.

## Metric Notes

- Positive latency overhead means Gateway is slower than the direct backend path.
- Negative RPS delta means Gateway achieved lower throughput than direct backend.
- Negative latency overhead can happen in local sequential runs due to run-to-run variance, warmup state, output length variance, and vLLM scheduling. It should be interpreted as no obvious Gateway bottleneck, not as proof that Gateway accelerates the backend.
- Compare runs only when prompts, stream mode, max tokens, and concurrency match.
- Output event counts are SSE chunks, not tokenizer-level output token counts.
