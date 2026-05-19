# Gateway Overhead Report

Generated at: `2026-05-19T19:48:58+00:00`

## Inputs

| Path | Result File | Base URL | Model | Mode | Requests/Level |
| --- | --- | --- | --- | --- | ---: |
| direct backend | benchmark/results/benchmark_1779219767.json | http://localhost:8000/v1 | Qwen/Qwen2.5-0.5B-Instruct | streaming | 100 |
| gateway | benchmark/results/benchmark_1779219615.json | http://localhost:8080/v1 | qwen-small | streaming | 100 |

## Direct Backend vs Gateway

| Concurrency | Direct RPS | Gateway RPS | RPS Delta | Direct P50 Latency (ms) | Gateway P50 Latency (ms) | P50 Overhead (ms) | Direct P95 Latency (ms) | Gateway P95 Latency (ms) | P95 Overhead (ms) | Direct P99 Latency (ms) | Gateway P99 Latency (ms) | P99 Overhead (ms) | Direct P50 TTFT (ms) | Gateway P50 TTFT (ms) | P50 TTFT Overhead (ms) | Direct P95 TTFT (ms) | Gateway P95 TTFT (ms) | P95 TTFT Overhead (ms) | Error Delta | Gateway Error Codes |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 1.73 | 1.85 | 6.90% | 354.46 | 356.79 | 2.33 | 1055.70 | 968.79 | -86.91 | 1076.18 | 974.88 | -101.30 | 32.11 | 40.46 | 8.35 | 43.47 | 52.54 | 9.07 | 0.00 pp | none |
| 4 | 5.57 | 5.90 | 5.82% | 453.51 | 395.46 | -58.05 | 1271.02 | 1187.33 | -83.69 | 1275.00 | 1199.88 | -75.12 | 43.46 | 53.76 | 10.30 | 54.05 | 86.16 | 32.11 | 0.00 pp | none |
| 8 | 9.28 | 9.49 | 2.28% | 506.08 | 492.28 | -13.80 | 1534.14 | 1458.64 | -75.50 | 1563.19 | 1479.05 | -84.14 | 45.24 | 57.36 | 12.12 | 87.38 | 146.26 | 58.88 | 0.00 pp | none |
| 16 | 12.82 | 14.15 | 10.36% | 741.09 | 668.38 | -72.71 | 2179.11 | 2031.30 | -147.81 | 2223.16 | 2054.39 | -168.77 | 53.92 | 81.65 | 27.73 | 150.34 | 262.63 | 112.29 | 0.00 pp | none |
| 32 | 17.17 | 17.08 | -0.51% | 1136.49 | 1244.51 | 108.02 | 3374.85 | 3297.35 | -77.50 | 3376.28 | 3300.85 | -75.43 | 75.08 | 114.42 | 39.34 | 266.73 | 491.56 | 224.83 | 0.00 pp | none |

## Prometheus Snapshot

| Snapshot File | Prometheus URL | Collected At |
| --- | --- | --- |
| benchmark/results/prometheus_snapshot_1779219891.json | http://localhost:9090 | 2026-05-19T19:44:51+00:00 |

| Metric | Status | Samples | Values |
| --- | --- | ---: | --- |
| gateway_error_rate_rps | success | 0 | no samples |
| gateway_output_chunks_per_second | success | 1 | model=qwen-small, backend_model=Qwen/Qwen2.5-0.5B-Instruct: 0.00 |
| gateway_p95_latency_seconds | success | 1 | 0.40 |
| gateway_p95_ttft_seconds | success | 1 | model=qwen-small, backend_model=Qwen/Qwen2.5-0.5B-Instruct: 0.08 |
| gateway_request_rate_rps | success | 1 | 0.27 |
| vllm_generation_tokens_per_second | success | 1 | model_name=Qwen/Qwen2.5-0.5B-Instruct: 0.00 |
| vllm_kv_cache_usage_percent | success | 0 | no samples |
| vllm_p95_e2e_latency_seconds | success | 1 | model_name=Qwen/Qwen2.5-0.5B-Instruct: 3.53 |
| vllm_p95_inter_token_latency_seconds | success | 0 | no samples |
| vllm_p95_ttft_seconds | success | 1 | model_name=Qwen/Qwen2.5-0.5B-Instruct: 0.07 |
| vllm_prompt_tokens_per_second | success | 1 | model_name=Qwen/Qwen2.5-0.5B-Instruct: 0.00 |
| vllm_running_requests | success | 1 | model_name=Qwen/Qwen2.5-0.5B-Instruct, job=vllm, instance=vllm:8000: 0.00 |
| vllm_waiting_requests | success | 1 | model_name=Qwen/Qwen2.5-0.5B-Instruct, job=vllm, instance=vllm:8000: 0.00 |

Prometheus snapshot values are point-in-time query results collected after the benchmark run. Empty samples usually mean the metric was absent, had no data in the query window, or is not exposed by the current backend/version.

## Metric Notes

- Positive latency overhead means Gateway is slower than the direct backend path.
- Negative RPS delta means Gateway achieved lower throughput than direct backend.
- Negative latency overhead can happen in local sequential runs due to run-to-run variance, warmup state, output length variance, and vLLM scheduling. It should be interpreted as no obvious Gateway bottleneck, not as proof that Gateway accelerates the backend.
- Compare runs only when prompts, stream mode, max tokens, and concurrency match.
- Output event counts are SSE chunks, not tokenizer-level output token counts.
