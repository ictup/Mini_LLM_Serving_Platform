# Benchmark Report

Generated at: `2026-05-17T17:00:28+00:00`

## Runs

| Result File | Base URL | Model | Mode | Requests/Level | Concurrency |
| --- | --- | --- | --- | ---: | --- |
| benchmark/results/benchmark_1779036601.json | http://127.0.0.1:8080/v1 | mock | non-streaming | 4 | 1, 2 |
| benchmark/results/benchmark_1779036895.json | http://127.0.0.1:8080/v1 | mock | streaming | 3 | 1 |

## Results

### `benchmark/results/benchmark_1779036601.json`

| Concurrency | Total | Success | Errors | RPS | P50 Latency (ms) | P95 Latency (ms) | P50 TTFT (ms) | P95 TTFT (ms) | Mean ITL (ms) | Output Events/s | Output Events | Error Rate |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 4 | 4 | 0 | 3.31 | 283.50 | 359.65 | n/a | n/a | n/a | n/a | n/a | 0.00% |
| 2 | 4 | 4 | 0 | 6.97 | 286.69 | 293.28 | n/a | n/a | n/a | n/a | n/a | 0.00% |

### `benchmark/results/benchmark_1779036895.json`

| Concurrency | Total | Success | Errors | RPS | P50 Latency (ms) | P95 Latency (ms) | P50 TTFT (ms) | P95 TTFT (ms) | Mean ITL (ms) | Output Events/s | Output Events | Error Rate |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 3 | 3 | 0 | 3.16 | 277.39 | 383.37 | 276.41 | 382.25 | 0.04 | 15.80 | 15 | 0.00% |

## Metric Notes

- E2E latency is measured from request start until the full response completes.
- TTFT is measured until the first non-empty streaming content chunk.
- ITL is the interval between non-empty streaming content chunks.
- Output events count SSE chunks with `delta.content`.
- Output token metrics are tokenizer-level only when the run was created with
  `--output-tokenizer-path`.
- TPOT is derived from tokenizer-level output tokens and streaming TTFT.
- Non-streaming runs show `n/a` for TTFT and ITL.
