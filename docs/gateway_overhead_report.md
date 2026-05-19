# Gateway Overhead Report

Generated at: `2026-05-19T20:43:20+00:00`

## Inputs

| Path | Result File | Base URL | Model | Mode | Requests/Level |
| --- | --- | --- | --- | --- | ---: |
| direct backend | benchmark/results/benchmark_1779222497.json | http://localhost:8000/v1 | Qwen/Qwen2.5-0.5B-Instruct | streaming | 100 |
| gateway | benchmark/results/benchmark_1779223297.json | http://localhost:8080/v1 | qwen-small | streaming | 100 |

## Direct Backend vs Gateway

| Concurrency | Direct RPS | Gateway RPS | RPS Delta | Direct P50 Latency (ms) | Gateway P50 Latency (ms) | P50 Overhead (ms) | Direct P95 Latency (ms) | Gateway P95 Latency (ms) | P95 Overhead (ms) | Direct P99 Latency (ms) | Gateway P99 Latency (ms) | P99 Overhead (ms) | Direct P50 TTFT (ms) | Gateway P50 TTFT (ms) | P50 TTFT Overhead (ms) | Direct P95 TTFT (ms) | Gateway P95 TTFT (ms) | P95 TTFT Overhead (ms) | Error Delta | Gateway Error Codes |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 1.73 | 1.98 | 14.83% | 369.68 | 304.97 | -64.71 | 1043.08 | 896.34 | -146.74 | 1079.73 | 904.84 | -174.89 | 31.16 | 39.27 | 8.11 | 44.47 | 49.78 | 5.31 | 0.00 pp | none |
| 4 | 5.71 | 6.31 | 10.61% | 464.32 | 370.43 | -93.89 | 1256.95 | 1119.99 | -136.96 | 1279.68 | 1140.63 | -139.05 | 42.89 | 50.63 | 7.74 | 57.51 | 85.77 | 28.26 | 0.00 pp | none |
| 8 | 9.45 | 10.14 | 7.27% | 507.77 | 479.28 | -28.49 | 1474.63 | 1368.80 | -105.83 | 1489.29 | 1389.05 | -100.24 | 45.35 | 54.08 | 8.73 | 98.91 | 146.56 | 47.65 | 0.00 pp | none |
| 16 | 13.58 | 14.19 | 4.49% | 693.88 | 683.34 | -10.54 | 2004.51 | 1902.34 | -102.17 | 2034.30 | 1965.12 | -69.18 | 49.89 | 70.16 | 20.27 | 134.05 | 257.35 | 123.30 | 0.00 pp | none |
| 32 | 17.87 | 16.11 | -9.84% | 1101.15 | 1447.24 | 346.09 | 3121.88 | 3529.36 | 407.48 | 3124.27 | 3585.54 | 461.27 | 67.98 | 169.88 | 101.90 | 268.89 | 472.72 | 203.83 | 0.00 pp | none |

## Prometheus Snapshot

| Snapshot File | Prometheus URL | Collected At |
| --- | --- | --- |
| benchmark/results/prometheus_snapshot_1779223391.json | http://localhost:9090 | 2026-05-19T20:43:10+00:00 |

| Metric | Status | Samples | Values |
| --- | --- | ---: | --- |
| gateway_error_rate_rps | success | 0 | no samples |
| gateway_output_chunks_per_second | success | 1 | model=qwen-small, backend_model=Qwen/Qwen2.5-0.5B-Instruct: 0.00 |
| gateway_p95_latency_seconds | success | 1 | 0.26 |
| gateway_p95_ttft_seconds | success | 1 | model=qwen-small, backend_model=Qwen/Qwen2.5-0.5B-Instruct: 0.09 |
| gateway_request_rate_rps | success | 1 | 0.27 |
| vllm_generation_tokens_per_second | success | 1 | model_name=Qwen/Qwen2.5-0.5B-Instruct: 0.00 |
| vllm_kv_cache_usage_percent | success | 1 | model_name=Qwen/Qwen2.5-0.5B-Instruct, job=vllm, instance=vllm:8000: 0.00 |
| vllm_p95_e2e_latency_seconds | success | 1 | model_name=Qwen/Qwen2.5-0.5B-Instruct: 2.80 |
| vllm_p95_inter_token_latency_seconds | success | 1 | model_name=Qwen/Qwen2.5-0.5B-Instruct: 0.03 |
| vllm_p95_ttft_seconds | success | 1 | model_name=Qwen/Qwen2.5-0.5B-Instruct: 0.08 |
| vllm_prompt_tokens_per_second | success | 1 | model_name=Qwen/Qwen2.5-0.5B-Instruct: 0.00 |
| vllm_running_requests | success | 1 | model_name=Qwen/Qwen2.5-0.5B-Instruct, job=vllm, instance=vllm:8000: 0.00 |
| vllm_waiting_requests | success | 1 | model_name=Qwen/Qwen2.5-0.5B-Instruct, job=vllm, instance=vllm:8000: 0.00 |

Prometheus snapshot values are point-in-time query results collected after the benchmark run. Empty samples usually mean the metric was absent, had no data in the query window, or is not exposed by the current backend/version.

## Prometheus Time Series Summary

| Time Series File | Prometheus URL | Started At | Ended At | Duration (s) | Interval (s) |
| --- | --- | --- | --- | ---: | ---: |
| benchmark/results/prometheus_timeseries_1779223382.json | http://localhost:9090 | 2026-05-19T20:40:02+00:00 | 2026-05-19T20:43:02+00:00 | 180.03 | 5.00 |

| Metric | Points | Samples | Min | Mean | Max | Last |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| gateway_error_rate_rps | 37 | 0 | n/a | n/a | n/a | n/a |
| gateway_output_chunks_per_second | 37 | 37 | 0.00 | 194.45 | 559.41 | 0.00 |
| gateway_p95_latency_seconds | 37 | 37 | 0.02 | 0.24 | 0.41 | 0.26 |
| gateway_p95_ttft_seconds | 37 | 37 | 0.04 | 0.08 | 0.10 | 0.09 |
| gateway_request_rate_rps | 37 | 37 | 0.25 | 3.02 | 8.11 | 0.27 |
| vllm_generation_tokens_per_second | 37 | 37 | 0.00 | 191.55 | 577.97 | 0.00 |
| vllm_kv_cache_usage_percent | 37 | 37 | 0.00 | 0.09 | 0.86 | 0.00 |
| vllm_p95_e2e_latency_seconds | 37 | 37 | 0.87 | 2.69 | 4.12 | 2.80 |
| vllm_p95_inter_token_latency_seconds | 37 | 37 | 0.01 | 0.03 | 0.04 | 0.03 |
| vllm_p95_ttft_seconds | 37 | 37 | 0.04 | 0.07 | 0.10 | 0.08 |
| vllm_prompt_tokens_per_second | 37 | 37 | 0.00 | 104.72 | 314.17 | 0.00 |
| vllm_running_requests | 37 | 37 | 0.00 | 2.76 | 32.00 | 0.00 |
| vllm_waiting_requests | 37 | 37 | 0.00 | 0.00 | 0.00 | 0.00 |

Prometheus time-series values are sampled while the benchmark is running. For gauges, max highlights peak pressure. For rate and histogram queries, mean/max summarize the query output over the sampling window.

## Metric Notes

- Positive latency overhead means Gateway is slower than the direct backend path.
- Negative RPS delta means Gateway achieved lower throughput than direct backend.
- Negative latency overhead can happen in local sequential runs due to run-to-run variance, warmup state, output length variance, and vLLM scheduling. It should be interpreted as no obvious Gateway bottleneck, not as proof that Gateway accelerates the backend.
- Compare runs only when prompts, stream mode, max tokens, and concurrency match.
- Output event counts are SSE chunks. Output token columns are tokenizer-level
  only when the benchmark run was created with `--output-tokenizer-path`.
