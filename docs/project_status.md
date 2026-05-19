# Project Status and Acceptance Checklist

This document is the current project checkpoint. It separates completed project
scope from intentionally excluded external integrations.

## Current Status

The project is a reproducible LLM serving platform with an OpenAI-compatible
Gateway, mock backend, vLLM GPU path, observability, benchmarking tools, Docker
Compose, Kubernetes manifests, Helm templates, and CI.

The vLLM path has been validated locally on an RTX 4060 Laptop GPU using
`Qwen/Qwen2.5-0.5B-Instruct` with `vllm/vllm-openai:v0.8.5.post1`. The larger
`Qwen/Qwen2.5-1.5B-Instruct` model remains a configurable option for machines
with more available GPU memory.

## Acceptance Checklist

| Area | Status | Evidence |
| --- | --- | --- |
| FastAPI Gateway process | Done | `gateway/app/main.py`, `/health`, `/ready` |
| OpenAI-compatible chat completions | Done | `/v1/chat/completions`, schema tests |
| Streaming SSE chat completions | Done | streaming proxy tests and SDK smoke test |
| OpenAI-compatible model list | Done | `/v1/models`, model alias tests |
| Mock backend | Done | `serving/mock_backend/app.py` |
| API key authentication | Done | `gateway/app/core/security.py` |
| Request IDs | Done | `gateway/app/core/request_id.py` |
| Redis RPM, TPM, and concurrent request limiting | Done | `gateway/app/core/rate_limit.py` |
| Request body and chat input limits | Done | `gateway/app/core/request_limits.py` |
| Structured logging | Done | `gateway/app/core/logging.py` |
| Prometheus metrics | Done | `gateway/app/observability/metrics.py` |
| Rejection reason metrics | Done | `gateway_http_rejections_total` |
| Grafana dashboards | Done | `monitoring/grafana/dashboards/*` |
| Local end-to-end smoke runner | Done | `scripts/local_e2e.py` |
| Benchmark runner | Done | `benchmark/run_benchmark.py` |
| Benchmark report generator | Done | `benchmark/generate_report.py` |
| Direct-vs-Gateway comparison tool | Done | `benchmark/compare_results.py` |
| Docker no-GPU stack | Done | `docker-compose.yml` |
| Docker vLLM GPU override | Done, locally validated | `docker-compose.gpu.yml`, `scripts/warmup_gateway.py` |
| Kubernetes no-GPU manifests | Done | `deploy/k8s` |
| Kubernetes vLLM GPU overlay | Implemented, template-validated | `deploy/k8s-gpu` |
| Helm chart | Done | `deploy/helm`, `helm lint`, `helm template` |
| GitHub Actions CI | Done | `.github/workflows/ci.yml` |
| Design decisions documentation | Done | `docs/design_decisions.md` |
| Failure analysis documentation | Done | `docs/failure_analysis.md` |
| RAG smoke test and integration guide | Done | `benchmark/rag_integration_smoke_test.py`, `docs/rag_integration.md` |
| External RAG application integration | Excluded from this completion | Requires a separate external RAG app path/config |
| Production ingress/TLS | Implemented as examples | `deploy/k8s/gateway-ingress.yaml`, Helm ingress values |
| Autoscaling | Implemented as examples | `deploy/k8s/gateway-hpa.yaml`, Helm autoscaling values |
| Secret management strategy | Implemented as examples | Helm `existingSecretName`, `deploy/k8s/examples/external-secrets.yaml` |
| vLLM startup and warmup handling | Implemented as examples | vLLM startup probes, `scripts/warmup_gateway.py` |
| Persistent dashboards/storage | Implemented for local stack | Docker `grafana-data` volume, dashboard JSON workflow |
| Local GPU benchmark report | Done | `docs/gateway_overhead_report.md` |
| Portfolio summary and demo script | Done | `docs/portfolio_summary.md` |

## Validation Commands

Run these locally after a fresh checkout:

```bash
uv sync --frozen --all-groups
uv run ruff check .
uv run pytest
uv run python scripts/local_e2e.py
```

Validate Kubernetes manifests:

```bash
kubectl kustomize deploy/k8s
kubectl kustomize deploy/k8s-gpu
```

Validate Helm:

```bash
helm lint deploy/helm
helm template mini-llm deploy/helm --namespace mini-llm-serving
helm template mini-llm deploy/helm \
  --namespace mini-llm-serving \
  --set vllm.enabled=true \
  --set mockBackend.enabled=false
```

Run the Docker no-GPU stack:

```bash
docker compose up --build
uv run python benchmark/client_smoke_test.py
docker compose down
```

## GPU/vLLM Validation Checklist

Validated locally on Windows + Docker Desktop + RTX 4060 Laptop GPU:

- `VLLM_IMAGE_TAG=v0.8.5.post1`
- `VLLM_MODEL=Qwen/Qwen2.5-0.5B-Instruct`
- Gateway warmup succeeded with `qwen-small`.
- OpenAI SDK non-streaming and streaming smoke test succeeded.
- Direct vLLM and Gateway streaming benchmarks completed with zero errors.
- Direct-vs-Gateway report generated at `docs/gateway_overhead_report.md`.

For another CUDA-capable host, repeat:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
uv run python scripts/warmup_gateway.py --model qwen-small
uv run python benchmark/client_smoke_test.py
```

## Known Limitations

- The mock backend is deterministic enough for platform testing, but it is not a
  substitute for real model latency, tokenization, or GPU scheduling behavior.
- vLLM has been locally verified with the 0.5B model. Larger models depend on
  available GPU memory and driver/container compatibility.
- Rate limiting uses an estimated token count instead of a model-specific
  tokenizer. This keeps the Gateway backend-neutral, but real token accounting
  may differ by model.
- Kubernetes and Helm assets include basic ingress, TLS, HPA, external Secret,
  and vLLM startup examples. They still do not include ServiceMonitor CRDs,
  cluster-specific GPU autoscaling, organization-specific secret stores,
  persistent cluster storage, or multi-model routing.
- Secrets in example manifests are local placeholders and must be replaced
  before any shared or public deployment.
- Grafana dashboards are provisioned for local experimentation. Long-term
  dashboard persistence is not configured.
- A project-local RAG smoke test is implemented. A specific external RAG
  application is intentionally excluded from this completion.

## Excluded Scope

- External RAG application integration. The serving platform exposes the
  OpenAI-compatible endpoint needed for that integration, but wiring a separate
  RAG codebase requires that project's path, configuration, and startup command.

## Documentation Map

| Document | Purpose |
| --- | --- |
| `README.md` | Quick start, main features, deployment entry points |
| `docs/api_usage.md` | Client-facing API examples and error shapes |
| `docs/configuration.md` | Runtime configuration matrix and secret handling |
| `docs/design_decisions.md` | Architecture choices and tradeoffs |
| `docs/failure_analysis.md` | Troubleshooting guide for common failures |
| `docs/production_hardening.md` | Ingress/TLS, secrets, autoscaling, vLLM readiness, Grafana persistence |
| `docs/gateway_overhead_report.md` | Local direct-vLLM vs Gateway benchmark comparison |
| `docs/performance_benchmarking.md` | Benchmark profiles, portfolio run commands, and metric interpretation |
| `docs/portfolio_summary.md` | Final project pitch, demo script, and CV bullets |
| `docs/rag_integration.md` | RAG client integration pattern and smoke test |
| `docs/benchmark_report.md` | Benchmark report template/output |
| `docs/project_status.md` | Acceptance checklist, limitations, and excluded scope |
