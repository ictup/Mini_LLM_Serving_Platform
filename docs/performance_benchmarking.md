# Performance Benchmarking Guide

This project separates smoke validation from portfolio-grade benchmark runs.
Smoke tests prove the path works. Portfolio runs are large enough to discuss
latency, TTFT, throughput, and Gateway overhead with evidence.

## Benchmark Profiles

| Profile | Concurrency | Requests/Level | Max Tokens | Warmup Requests | Use |
| --- | --- | ---: | ---: | ---: | --- |
| `smoke` | `1, 2, 4` | 10 | 64 | 0 | Fast local sanity check |
| `portfolio` | `1, 4, 8, 16, 32` | 100 | 128 | 10 | Resume/GitHub benchmark evidence |
| `stress` | `1, 4, 8, 16, 32` | 1000 | 128 | 20 | Longer saturation run |

Explicit CLI flags override profile defaults. For example, use
`--profile portfolio --requests-per-level 300` when you want a larger run
without changing the concurrency plan.

## Direct vLLM Run

Direct vLLM does not pass through Gateway rate limiting:

```bash
uv run python benchmark/run_benchmark.py \
  --profile portfolio \
  --base-url http://localhost:8000/v1 \
  --api-key local-vllm-key \
  --model Qwen/Qwen2.5-0.5B-Instruct \
  --prompts benchmark/prompts/short_prompts.jsonl \
  --timeout-seconds 120 \
  --stream true
```

## Gateway Run

For Gateway capacity benchmarking, raise the local demo rate limits before
starting Compose. Otherwise the default `RATE_LIMIT_RPM=60` and
`RATE_LIMIT_TPM=60000` will intentionally reject the portfolio profile:

```powershell
$env:RATE_LIMIT_RPM="10000"
$env:RATE_LIMIT_TPM="2000000"
$env:RATE_LIMIT_CONCURRENT_REQUESTS="64"
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

This keeps rate limiting implemented and observable while preventing tenant
quota settings from dominating a raw serving-capacity benchmark.

```bash
uv run python benchmark/run_benchmark.py \
  --profile portfolio \
  --base-url http://localhost:8080/v1 \
  --api-key dev-key \
  --model qwen-small \
  --prompts benchmark/prompts/short_prompts.jsonl \
  --timeout-seconds 120 \
  --stream true
```

## Report Generation

```bash
uv run python benchmark/compare_results.py \
  --direct-result benchmark/results/<direct-result>.json \
  --gateway-result benchmark/results/<gateway-result>.json \
  --prometheus-snapshot benchmark/results/<prometheus-snapshot>.json \
  --output docs/gateway_overhead_report.md
```

For multiple benchmark files:

```bash
uv run python benchmark/generate_report.py \
  --results benchmark/results \
  --output docs/benchmark_report.md
```

## Prometheus Snapshot

After a benchmark run, collect a Gateway and vLLM metrics snapshot from
Prometheus:

```bash
uv run python benchmark/collect_prometheus_snapshot.py \
  --prometheus-url http://localhost:9090
```

The snapshot is written to `benchmark/results/prometheus_snapshot_*.json`. It
includes Gateway request/error rate, Gateway latency and TTFT queries, vLLM
running/waiting request gauges, KV cache usage, token throughput, and vLLM
latency histogram queries.

Pass the snapshot path to `benchmark/compare_results.py` to include a
point-in-time metrics table in `docs/gateway_overhead_report.md`.

## Recorded Metrics

The benchmark runner records:

- RPS and error rate.
- Error status-code and OpenAI error-code distributions.
- P50, P95, and P99 end-to-end latency.
- P50, P95, and P99 TTFT for streaming runs.
- P50, P95, and mean inter-token latency proxy.
- Output SSE content events per second.
- Output SSE content event count.
- Run profile, prompt file, max tokens, warmup count, timeout, and concurrency.

Output events are SSE chunks with `delta.content`, not tokenizer-level output
tokens. Tokenizer-accurate output tokens/sec is a later enhancement.

## Interpretation

A good portfolio benchmark should show:

- Zero or near-zero error rate at low and moderate concurrency.
- If errors appear, the `error_codes` field should make the cause explicit, for
  example `rate_limit_exceeded`, `token_rate_limit_exceeded`, backend errors,
  or client timeouts.
- Gateway RPS close to direct vLLM RPS.
- Gateway P95/P99 latency close to direct vLLM latency.
- Stable TTFT under increasing concurrency.
- A clear saturation point where waiting, latency, or error rate starts rising.

When the GPU path is stable, keep one small validated snapshot in the README
and link to the full generated report for details.
