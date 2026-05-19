# Failure Analysis

This document is a practical troubleshooting guide for the current project. It
focuses on the failures most likely to happen while running the Gateway locally,
through Docker Compose, or against vLLM.

## First Checks

Before debugging a specific failure, collect these facts:

- The request `X-Request-ID`.
- The Gateway mode: `BACKEND_TYPE=mock` or `BACKEND_TYPE=vllm`.
- The requested model alias.
- Whether the request is streaming.
- Gateway logs for the same request ID.
- `/ready` response.
- `/metrics` output or Grafana panels.
- Backend health: mock `/v1/models` or vLLM `/v1/models`.

## Backend Timeout

Symptoms:

- Client receives `504`.
- Error envelope has `code=backend_timeout`.
- `/ready` may still pass if the backend responds to `/v1/models`.
- Long completions or saturated GPU backends are more likely to trigger it.

Likely causes:

- `BACKEND_TIMEOUT_SECONDS` is too low for non-streaming calls.
- `STREAMING_TIMEOUT_SECONDS` is too low for long streaming calls.
- vLLM is still loading the model.
- The backend is saturated or queueing.
- The Gateway points to the wrong backend URL.

Checks:

```bash
curl http://localhost:8080/ready
curl http://localhost:9000/v1/models
curl http://localhost:8000/v1/models -H "Authorization: Bearer local-vllm-key"
```

Fixes:

- Increase `BACKEND_TIMEOUT_SECONDS` or `STREAMING_TIMEOUT_SECONDS`.
- Confirm `MOCK_BASE_URL` or `VLLM_BASE_URL` uses the right service name for the
  current environment.
- Wait for vLLM model loading to finish before benchmarking.
- Reduce concurrency in the benchmark runner and compare again.
- Check vLLM engine metrics for queueing and KV cache pressure.

## Backend Unavailable

Symptoms:

- `/ready` returns `503`.
- Chat requests return a backend error.
- Gateway logs show a backend connection or upstream error.

Likely causes:

- Mock backend or vLLM process is not running.
- Docker service DNS name is wrong for the current environment.
- Port-forward is missing in Kubernetes.
- vLLM requires an API key and `VLLM_API_KEY` does not match.

Checks:

```bash
curl http://localhost:8080/ready
docker compose ps
kubectl -n mini-llm-serving get pods
kubectl -n mini-llm-serving get svc
```

Fixes:

- Start the missing backend service.
- Use Docker service URLs inside Compose, such as `http://mock-backend:9000/v1`
  or `http://vllm:8000/v1`.
- Use localhost URLs only from the host machine.
- Confirm Gateway and vLLM use the same `VLLM_API_KEY`.

## Streaming Broken

Symptoms:

- Non-streaming requests work but streaming hangs.
- Client receives one large response instead of incremental chunks.
- curl does not show chunks as they arrive.
- SDK streaming loop returns no content.

Likely causes:

- Client forgot to set `stream=true`.
- curl is buffering output.
- A proxy or ingress buffers SSE.
- Backend sends malformed SSE frames.
- Gateway response is not using `text/event-stream`.

Checks:

```bash
curl -N http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer dev-key" \
  -H "Content-Type: application/json" \
  -d '{"model":"mock","messages":[{"role":"user","content":"stream test"}],"stream":true}'
```

Fixes:

- Use `curl -N` for manual streaming tests.
- Confirm the request body includes `"stream": true`.
- Avoid buffering reverse proxies for SSE paths.
- Check that response headers include `Cache-Control: no-cache` and
  `X-Accel-Buffering: no`.
- Re-run `uv run python benchmark/client_smoke_test.py` to verify SDK behavior.

## Authentication Failure

Symptoms:

- Client receives `401`.
- Error envelope has `code=invalid_api_key`.
- Response includes `WWW-Authenticate: Bearer`.

Likely causes:

- Missing `Authorization` header.
- Wrong scheme, such as `Token` instead of `Bearer`.
- API key is not listed in `API_KEYS`.
- Client is confusing `API_KEYS` with `VLLM_API_KEY`.

Checks:

```bash
curl http://localhost:8080/v1/models -H "Authorization: Bearer dev-key"
```

Fixes:

- Use `Authorization: Bearer <gateway-client-key>` for client-to-Gateway calls.
- Set `API_KEYS` to the comma-separated client keys accepted by the Gateway.
- Use `VLLM_API_KEY` only for Gateway-to-vLLM traffic.

## Model Not Found

Symptoms:

- Client receives `400`.
- Error envelope has `code=model_not_found`.
- `/v1/models` does not list the model the client requested.

Likely causes:

- The client sent a raw backend model id when the Gateway expects an alias.
- `MODEL_ALIASES_JSON` is missing the alias.
- `MODEL_ALIASES_JSON` is invalid JSON.

Checks:

```bash
curl http://localhost:8080/v1/models -H "Authorization: Bearer dev-key"
```

Fixes:

- Call a model alias listed by `/v1/models`.
- Set `DEFAULT_MODEL` to a client-facing alias.
- Set `MODEL_ALIASES_JSON` to a valid JSON object, for example:

```env
MODEL_ALIASES_JSON={"qwen-small":"Qwen/Qwen2.5-1.5B-Instruct"}
```

## Rate Limit False Positive

Symptoms:

- Client receives `429` earlier than expected.
- One user appears to consume another user's quota.
- Local E2E passes, but Docker or Kubernetes traffic gets rate limited.

Likely causes:

- Multiple clients share the same API key.
- Redis still contains counters from a previous run.
- `RATE_LIMIT_RPM` is too low for benchmark concurrency.
- Clock or key naming assumptions differ between environments.

Checks:

```bash
docker compose exec redis redis-cli keys '*'
docker compose exec redis redis-cli ttl <rate-limit-key>
```

Fixes:

- Use separate API keys for separate clients or tests.
- Increase `RATE_LIMIT_RPM` for benchmark runs.
- Flush local Redis only in development if stale counters are suspected.
- Disable rate limiting for isolated local E2E tests when Redis is not part of
  the scenario.

## High p95 Latency

Symptoms:

- Average latency looks acceptable, but p95 is high.
- TTFT is high in streaming benchmarks.
- Grafana latency panels spike under concurrency.

Likely causes:

- Backend queueing.
- GPU saturation in vLLM.
- Too much benchmark concurrency for the selected model.
- Redis latency or rate-limit overhead.
- Gateway logging or metrics overhead.
- Client connection setup overhead.

Checks:

- Compare direct backend benchmark vs Gateway benchmark.
- Check Gateway latency and streaming TTFT metrics.
- Check vLLM engine metrics for waiting requests, running requests, KV cache
  usage, and token throughput.
- Re-run benchmarks with lower concurrency.

Fixes:

- Reduce benchmark concurrency or request size.
- Tune vLLM model, dtype, and GPU allocation.
- Reuse HTTP clients where possible.
- Keep metrics labels low cardinality.
- Confirm Redis is close to Gateway in deployed environments.

## Gateway Overhead Too High

Symptoms:

- Direct vLLM benchmark is much faster than Gateway-routed benchmark.
- Gateway p95 latency grows while backend metrics look healthy.
- Streaming TTFT is much higher through Gateway than direct backend.

Likely causes:

- HTTP connection reuse is poor.
- Streaming chunks are buffered by a proxy.
- Redis rate-limit calls are slow.
- Logs are too verbose or synchronous sinks are slow.
- Metrics labels are too high cardinality.
- Gateway timeout settings cause retries or slow failure paths.

Checks:

```bash
uv run python benchmark/compare_results.py \
  --direct-result benchmark/results/<direct>.json \
  --gateway-result benchmark/results/<gateway>.json \
  --output docs/gateway_overhead_report.md
```

Fixes:

- Compare direct and Gateway runs with the same prompt set and concurrency.
- Disable optional components one at a time in a local test to isolate overhead.
- Keep raw prompt logging disabled.
- Avoid adding per-user or per-request labels to Prometheus metrics.
- Verify proxies do not buffer SSE.

## Metrics Missing

Symptoms:

- `/metrics` returns `404`.
- Prometheus target is down.
- Grafana dashboard panels are empty.

Likely causes:

- `METRICS_ENABLED=false`.
- Prometheus is scraping the wrong host or port.
- No requests have been sent yet.
- The dashboard query expects labels that have not appeared.
- vLLM scrape config is enabled but vLLM is not running.

Checks:

```bash
curl http://localhost:8080/metrics
curl http://localhost:9090/targets
```

Fixes:

- Set `METRICS_ENABLED=true`.
- Confirm Prometheus config matches the runtime mode.
- Send a few requests through the Gateway.
- In no-GPU mode, expect vLLM-specific panels to be empty.

## Kubernetes or Helm Deployment Fails

Symptoms:

- Pods remain pending or crash looping.
- Gateway readiness fails.
- Helm template renders but deployed service is not reachable.

Likely causes:

- Local image `mini-llm-serving-platform:local` is not available in the cluster.
- GPU overlay is applied to a cluster without NVIDIA GPU support.
- Secret placeholders were not replaced.
- Service names differ from expected Gateway backend URLs.

Checks:

```bash
kubectl kustomize deploy/k8s
kubectl kustomize deploy/k8s-gpu
helm template mini-llm deploy/helm --namespace mini-llm-serving
kubectl -n mini-llm-serving describe pod <pod-name>
kubectl -n mini-llm-serving logs <pod-name>
```

Fixes:

- Build and load the local image into the target cluster.
- Use the no-GPU base manifests unless GPU support is available.
- Replace example Secret values before shared deployments.
- Confirm Gateway config points to `mock-backend:9000` or `vllm:8000` inside the
  cluster.
