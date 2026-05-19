# Gateway Overhead Report

Generated at: `2026-05-19T19:28:14+00:00`

## Inputs

| Path | Result File | Base URL | Model | Mode | Requests/Level |
| --- | --- | --- | --- | --- | ---: |
| direct backend | benchmark/results/benchmark_1779218848.json | http://localhost:8000/v1 | Qwen/Qwen2.5-0.5B-Instruct | streaming | 100 |
| gateway | benchmark/results/benchmark_1779218609.json | http://localhost:8080/v1 | qwen-small | streaming | 100 |

## Direct Backend vs Gateway

| Concurrency | Direct RPS | Gateway RPS | RPS Delta | Direct P50 Latency (ms) | Gateway P50 Latency (ms) | P50 Overhead (ms) | Direct P95 Latency (ms) | Gateway P95 Latency (ms) | P95 Overhead (ms) | Direct P99 Latency (ms) | Gateway P99 Latency (ms) | P99 Overhead (ms) | Direct P50 TTFT (ms) | Gateway P50 TTFT (ms) | P50 TTFT Overhead (ms) | Direct P95 TTFT (ms) | Gateway P95 TTFT (ms) | P95 TTFT Overhead (ms) | Error Delta | Gateway Error Codes |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 1.15 | 1.47 | 27.72% | 549.03 | 433.13 | -115.90 | 1630.03 | 1242.91 | -387.12 | 1766.17 | 1278.05 | -488.12 | 41.75 | 46.38 | 4.63 | 49.10 | 61.71 | 12.61 | 0.00 pp | none |
| 4 | 3.77 | 4.71 | 24.99% | 654.16 | 525.07 | -129.09 | 1973.45 | 1524.16 | -449.29 | 2052.64 | 1535.96 | -516.68 | 46.64 | 61.33 | 14.69 | 64.02 | 87.43 | 23.41 | 0.00 pp | none |
| 8 | 6.32 | 7.75 | 22.67% | 730.06 | 656.18 | -73.88 | 2222.24 | 1798.30 | -423.94 | 2237.56 | 1829.07 | -408.49 | 48.06 | 70.76 | 22.70 | 115.20 | 163.79 | 48.59 | 0.00 pp | none |
| 16 | 8.82 | 11.34 | 28.54% | 1056.36 | 927.37 | -128.99 | 3022.67 | 2469.14 | -553.53 | 3088.89 | 2471.07 | -617.82 | 59.58 | 79.86 | 20.28 | 177.19 | 287.39 | 110.20 | 0.00 pp | none |
| 32 | 11.09 | 14.53 | 31.00% | 1769.09 | 1522.80 | -246.29 | 4901.53 | 3960.98 | -940.55 | 4903.18 | 3964.46 | -938.72 | 90.75 | 205.41 | 114.66 | 354.04 | 700.08 | 346.04 | 0.00 pp | none |

## Metric Notes

- Positive latency overhead means Gateway is slower than the direct backend path.
- Negative RPS delta means Gateway achieved lower throughput than direct backend.
- Negative latency overhead can happen in local sequential runs due to run-to-run variance, warmup state, output length variance, and vLLM scheduling. It should be interpreted as no obvious Gateway bottleneck, not as proof that Gateway accelerates the backend.
- Compare runs only when prompts, stream mode, max tokens, and concurrency match.
- Output event counts are SSE chunks, not tokenizer-level output token counts.
