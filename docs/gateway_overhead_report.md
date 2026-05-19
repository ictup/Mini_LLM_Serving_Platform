# Gateway Overhead Report

Generated at: `2026-05-19T18:23:22+00:00`

Validation environment:

- GPU: NVIDIA GeForce RTX 4060 Laptop GPU, 8GB VRAM.
- Host driver reported CUDA support: 12.7.
- vLLM image: `vllm/vllm-openai:v0.8.5.post1`.
- Served model: `Qwen/Qwen2.5-0.5B-Instruct`.
- Gateway model alias: `qwen-small`.

The benchmark result JSON files under `benchmark/results/` are local run
artifacts and are intentionally ignored by Git. This report keeps the summarized
comparison in versioned documentation.

## Inputs

| Path | Result File | Base URL | Model | Mode | Requests/Level |
| --- | --- | --- | --- | --- | ---: |
| direct backend | benchmark/results/benchmark_1779214994.json | http://localhost:8000/v1 | Qwen/Qwen2.5-0.5B-Instruct | streaming | 5 |
| gateway | benchmark/results/benchmark_1779214918.json | http://localhost:8080/v1 | qwen-small | streaming | 5 |

## Direct Backend vs Gateway

| Concurrency | Direct RPS | Gateway RPS | RPS Delta | Direct P50 Latency (ms) | Gateway P50 Latency (ms) | P50 Overhead (ms) | Direct P95 Latency (ms) | Gateway P95 Latency (ms) | P95 Overhead (ms) | Direct P50 TTFT (ms) | Gateway P50 TTFT (ms) | TTFT Overhead (ms) | Error Delta |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 2.25 | 2.25 | 0.00% | 515.52 | 440.63 | -74.89 | 585.91 | 587.33 | 1.42 | 34.29 | 52.14 | 17.85 | 0.00 pp |
| 2 | 3.92 | 3.81 | -2.74% | 366.83 | 442.53 | 75.70 | 625.46 | 605.28 | -20.18 | 43.57 | 49.24 | 5.67 | 0.00 pp |

## Metric Notes

- Positive latency overhead means Gateway is slower than the direct backend path.
- Negative RPS delta means Gateway achieved lower throughput than direct backend.
- Compare runs only when prompts, stream mode, max tokens, and concurrency match.
- Output event counts are SSE chunks, not tokenizer-level output token counts.
- The sample size is intentionally small for local portfolio validation. Use
  larger request counts for more stable production capacity analysis.
