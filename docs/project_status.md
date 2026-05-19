# Project Status and Acceptance Checklist

This document is the current project checkpoint. It separates the implemented
MVP from the work that still requires a GPU environment, external systems, or
production infrastructure decisions.

## Current Status

The project is a reproducible no-GPU LLM serving platform with an
OpenAI-compatible Gateway, mock backend, observability, benchmarking tools,
Docker Compose, Kubernetes manifests, Helm templates, and CI.

The vLLM path is implemented as configuration, Docker Compose override,
Kubernetes overlay, Helm values, metrics scraping, and benchmark commands. It
still needs validation on a real CUDA-capable machine before it should be
presented as fully benchmarked.

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
| Redis RPM rate limiting | Done | `gateway/app/core/rate_limit.py` |
| Structured logging | Done | `gateway/app/core/logging.py` |
| Prometheus metrics | Done | `gateway/app/observability/metrics.py` |
| Grafana dashboards | Done | `monitoring/grafana/dashboards/*` |
| Local end-to-end smoke runner | Done | `scripts/local_e2e.py` |
| Benchmark runner | Done | `benchmark/run_benchmark.py` |
| Benchmark report generator | Done | `benchmark/generate_report.py` |
| Direct-vs-Gateway comparison tool | Done | `benchmark/compare_results.py` |
| Docker no-GPU stack | Done | `docker-compose.yml` |
| Docker vLLM GPU override | Implemented, needs GPU validation | `docker-compose.gpu.yml` |
| Kubernetes no-GPU manifests | Done | `deploy/k8s` |
| Kubernetes vLLM GPU overlay | Implemented, needs GPU cluster validation | `deploy/k8s-gpu` |
| Helm chart | Done | `deploy/helm`, `helm lint`, `helm template` |
| GitHub Actions CI | Done | `.github/workflows/ci.yml` |
| Design decisions documentation | Done | `docs/design_decisions.md` |
| Failure analysis documentation | Done | `docs/failure_analysis.md` |
| RAG smoke test and integration guide | Done | `benchmark/rag_integration_smoke_test.py`, `docs/rag_integration.md` |
| External RAG application integration | Not implemented | Needs an external RAG app path/config |
| Production ingress/TLS | Not implemented | Future work |
| Autoscaling | Not implemented | Future work |
| Persistent dashboards/storage | Not implemented | Future work |

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

Use this checklist on a CUDA-capable host:

- Confirm Docker can access the GPU with `nvidia-smi` inside a CUDA container.
- Set `VLLM_MODEL`, `VLLM_API_KEY`, and `HUGGING_FACE_HUB_TOKEN` if needed.
- Start the GPU stack with `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build`.
- Confirm vLLM responds at `http://localhost:8000/v1/models`.
- Confirm Gateway readiness returns `backend_type=vllm`.
- Run `benchmark/client_smoke_test.py` with `LLM_MODEL=qwen-small`.
- Run direct vLLM and Gateway benchmark commands from the README.
- Generate the direct-vs-Gateway overhead report.
- Check Prometheus targets for both `gateway` and `vllm`.
- Check Grafana `Gateway Overview` and `vLLM Engine Overview` dashboards.

## Known Limitations

- The mock backend is deterministic enough for platform testing, but it is not a
  substitute for real model latency, tokenization, or GPU scheduling behavior.
- vLLM deployment files are implemented but not verified in this workspace on
  actual GPU hardware.
- Rate limiting is request-per-minute only. Token-per-minute limiting is not
  implemented.
- Kubernetes and Helm assets are intentionally minimal. They do not include
  ingress, TLS, HPA, ServiceMonitor CRDs, persistent volumes, external secrets,
  or multi-model routing.
- Secrets in example manifests are local placeholders and must be replaced
  before any shared or public deployment.
- Grafana dashboards are provisioned for local experimentation. Long-term
  dashboard persistence is not configured.
- A project-local RAG smoke test is implemented. A specific external RAG
  application has not been wired to this Gateway yet.

## Production Hardening Backlog

- Add token-per-minute and concurrent-request rate limiting.
- Add request body size limits and stricter validation for operational safety.
- Add ingress/TLS examples and a deployment-specific secret management strategy.
- Add HPA or queue-aware autoscaling recommendations.
- Add model warmup and backend startup readiness behavior for real vLLM models.
- Add persistent Grafana storage or dashboard export workflow.
- Connect an external RAG application to this Gateway when its path/config is
  available.
- Add real GPU benchmark results and a finalized gateway overhead report.

## Documentation Map

| Document | Purpose |
| --- | --- |
| `README.md` | Quick start, main features, deployment entry points |
| `docs/api_usage.md` | Client-facing API examples and error shapes |
| `docs/configuration.md` | Runtime configuration matrix and secret handling |
| `docs/design_decisions.md` | Architecture choices and tradeoffs |
| `docs/failure_analysis.md` | Troubleshooting guide for common failures |
| `docs/rag_integration.md` | RAG client integration pattern and smoke test |
| `docs/benchmark_report.md` | Benchmark report template/output |
| `docs/project_status.md` | Acceptance checklist, limitations, and next work |
