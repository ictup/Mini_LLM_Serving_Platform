# Mini LLM Serving Platform

A production-style OpenAI-compatible LLM serving gateway built step by step from
the implementation blueprint.

## Quick start

Run the local no-GPU smoke test:

```bash
uv sync --frozen --all-groups
uv run python scripts/local_e2e.py
```

Run the quality gate:

```bash
uv run ruff check .
uv run pytest
```

Start the Docker no-GPU stack:

```bash
docker compose up --build
```

## Implemented capabilities

- FastAPI Gateway with `GET /health`, `GET /ready`, `GET /metrics`, `GET /v1/models`, and `POST /v1/chat/completions`.
- OpenAI-compatible chat completion schemas for non-streaming and streaming requests.
- Mock OpenAI-compatible backend for reproducible no-GPU development and CI.
- Gateway proxying to mock or vLLM backends.
- Streaming SSE proxy with client-facing model alias rewriting.
- Bearer API key authentication.
- Request ID propagation with `X-Request-ID`.
- Redis-backed per-API-key RPM rate limiting.
- Structured JSON logging with `structlog`.
- Prometheus metrics for request volume, errors, latency, and streaming behavior.
- Configurable model aliases for stable client-facing names.
- OpenAI Python SDK smoke test for non-streaming and streaming completions.
- Local end-to-end smoke runner for mock backend plus Gateway.
- Async benchmark runner with latency, throughput, error rate, TTFT, and ITL metrics.
- Markdown benchmark report generator and direct-vs-Gateway comparison tool.
- Docker Compose no-GPU stack with Gateway, mock backend, Redis, Prometheus, and Grafana.
- Optional Docker Compose GPU override for vLLM.
- Kubernetes no-GPU manifests for Gateway, mock backend, Redis, and Prometheus.
- Kubernetes GPU overlay for vLLM.
- Minimal Helm chart for mock and vLLM modes.
- GitHub Actions CI for Python checks and Helm chart validation.

Direct vLLM benchmark comparison is available through the benchmark scripts.

See `docs/project_status.md` for the acceptance checklist, validation commands,
known limitations, and remaining production hardening work.

## Continuous integration

The repository includes a GitHub Actions workflow at
`.github/workflows/ci.yml`. It runs on pushes to `main` and on pull requests.

Checks:

- `uv sync --frozen --all-groups`
- `uv run ruff check .`
- `uv run pytest`
- `helm lint deploy/helm`
- Helm template rendering for both the default mock stack and the optional vLLM stack

## Configuration

Copy `.env.example` to `.env` for local process development. For Docker,
Kubernetes, and Helm deployments, see the configuration matrix in
`docs/configuration.md`.

## API usage

The Gateway exposes OpenAI-compatible `/v1/models` and `/v1/chat/completions`
endpoints. See `docs/api_usage.md` for curl examples, Python SDK examples,
streaming usage, error responses, and health check behavior.

## Design and operations docs

- `docs/design_decisions.md`: explains the main architecture choices.
- `docs/failure_analysis.md`: lists common failures and debugging steps.
- `docs/rag_integration.md`: shows how a RAG app can call the Gateway.
- `docs/project_status.md`: tracks completed capabilities, limitations, and remaining work.

## Local end-to-end smoke test

Run a full local mock stack and SDK smoke test with one command:

```bash
make local-e2e
```

Or run the script directly:

```bash
uv run python scripts/local_e2e.py
```

This starts the mock backend, starts the Gateway in mock mode, waits for
readiness, runs `benchmark/client_smoke_test.py`, and then stops both services.

## Docker Compose no-GPU stack

Start the local reproducible stack:

```bash
docker compose up --build
```

Services:

- Gateway: http://localhost:8080
- Mock backend: http://localhost:9000
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000, login `admin` / `admin`
- Redis: localhost:6379

Grafana automatically loads the `Gateway Overview` dashboard from
`monitoring/grafana/dashboards/gateway-overview.json`. The dashboard includes
HTTP request rate, error rate, latency, streaming TTFT, streaming duration, and
streaming output chunk rate.

Smoke test through the Gateway:

```bash
uv run python benchmark/client_smoke_test.py
```

Stop the stack:

```bash
docker compose down
```

## Docker Compose GPU stack

When a CUDA-capable Docker runtime is available, run the vLLM override:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

Important environment variables:

- `VLLM_MODEL`: model served by vLLM, default `Qwen/Qwen2.5-1.5B-Instruct`
- `VLLM_API_KEY`: internal Gateway-to-vLLM API key, default `local-vllm-key`
- `HUGGING_FACE_HUB_TOKEN`: required only for gated Hugging Face models
- `VLLM_DTYPE`: vLLM dtype setting, default `auto`

In GPU mode, Gateway uses `BACKEND_TYPE=vllm` and routes the client-facing
`qwen-small` alias to `VLLM_MODEL`.

GPU mode also switches Prometheus to `monitoring/prometheus/prometheus.gpu.yml`,
which scrapes both Gateway and vLLM. Grafana automatically loads a separate
`vLLM Engine Overview` dashboard for scheduler state, KV cache usage, TTFT,
E2E latency, inter-token latency, and token throughput.

## Direct vLLM vs Gateway benchmark

Run the same prompt set against vLLM directly and through the Gateway:

```bash
uv run python benchmark/run_benchmark.py \
  --base-url http://localhost:8000/v1 \
  --api-key local-vllm-key \
  --model Qwen/Qwen2.5-1.5B-Instruct \
  --prompts benchmark/prompts/short_prompts.jsonl \
  --concurrency 1 2 4 \
  --requests-per-level 10 \
  --stream true

uv run python benchmark/run_benchmark.py \
  --base-url http://localhost:8080/v1 \
  --api-key dev-key \
  --model qwen-small \
  --prompts benchmark/prompts/short_prompts.jsonl \
  --concurrency 1 2 4 \
  --requests-per-level 10 \
  --stream true
```

Generate the overhead report from the two result JSON files:

```bash
uv run python benchmark/compare_results.py \
  --direct-result benchmark/results/<direct-result>.json \
  --gateway-result benchmark/results/<gateway-result>.json \
  --output docs/gateway_overhead_report.md
```

## Kubernetes no-GPU manifests

The minimal Kubernetes manifests live in `deploy/k8s` and cover Gateway, mock
backend, Redis, and Prometheus. They use the local image name
`mini-llm-serving-platform:local`, so build and load that image into your local
cluster before applying the manifests.

```bash
kubectl apply -k deploy/k8s
kubectl -n mini-llm-serving port-forward svc/gateway 8080:8080
kubectl -n mini-llm-serving port-forward svc/prometheus 9090:9090
```

Remove the stack:

```bash
kubectl delete -k deploy/k8s
```

## Kubernetes GPU overlay

The GPU overlay in `deploy/k8s-gpu` reuses the no-GPU base and adds vLLM. It
patches Gateway to use `BACKEND_TYPE=vllm`, routes `qwen-small` to
`Qwen/Qwen2.5-1.5B-Instruct`, and patches Prometheus to scrape `vllm:8000`.

```bash
kubectl apply -k deploy/k8s-gpu
kubectl -n mini-llm-serving port-forward svc/gateway 8080:8080
kubectl -n mini-llm-serving port-forward svc/vllm 8000:8000
```

The vLLM deployment requests one NVIDIA GPU with `nvidia.com/gpu: "1"`. Replace
the example `local-vllm-key` and optional Hugging Face token Secret values
before using this outside local experiments.

## Helm chart

The minimal Helm chart lives in `deploy/helm`. By default it deploys the same
no-GPU stack as `deploy/k8s`: Gateway, mock backend, Redis, and Prometheus.

```bash
helm template mini-llm deploy/helm --namespace mini-llm-serving
helm upgrade --install mini-llm deploy/helm --namespace mini-llm-serving --create-namespace
```

Enable vLLM with values:

```bash
helm template mini-llm deploy/helm \
  --namespace mini-llm-serving \
  --set vllm.enabled=true \
  --set mockBackend.enabled=false
```

The chart is intentionally small. Use it as a deployment skeleton before adding
production concerns such as ingress, persistent storage, ServiceMonitor CRDs,
autoscaling, or secret management integration.
