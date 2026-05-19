# Portfolio Summary

## Project Pitch

This project is a production-style OpenAI-compatible LLM serving gateway. It
places a FastAPI platform layer in front of mock or vLLM backends and adds the
features commonly needed around model serving: authentication, request IDs,
model aliases, weighted routing, Redis-backed RPM/TPM/concurrency limits,
structured logging, Prometheus metrics, Grafana dashboards, alert rules,
streaming proxying, Docker Compose, Kubernetes, Helm, GitOps, Terraform,
supply-chain checks, release automation, and benchmark reporting.

The local no-GPU path uses a mock backend so the repository remains
reproducible in CI and on laptops. The GPU path has been validated with
`vllm/vllm-openai:v0.8.5.post1` and `Qwen/Qwen2.5-0.5B-Instruct` on an RTX 4060
Laptop GPU.

## Two-Minute Demo Script

1. Show the architecture: OpenAI-compatible client -> Gateway -> mock or vLLM.
2. Run `uv run python scripts/local_e2e.py` to prove the no-GPU path.
3. Start GPU mode with `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build`.
4. Run `uv run python scripts/warmup_gateway.py --model qwen-small`.
5. Run `uv run python benchmark/client_smoke_test.py` with `LLM_MODEL=qwen-small`.
6. Open Grafana and show Gateway request rate, latency, streaming TTFT, and rejection reason panels.
7. Open `docs/gateway_overhead_report.md` and explain direct backend vs Gateway overhead.
8. Close with the production boundaries: this is a production-style portfolio
   gateway, not a full enterprise GPU scheduler or multi-tenant billing system.

## CV Bullets

OpenAI-Compatible LLM Serving Platform with vLLM and Production Tooling

Python, FastAPI, vLLM, Redis, Prometheus, Grafana, Docker, Kubernetes, Helm,
Argo CD, Terraform, GitHub Actions

- Built a FastAPI gateway in front of mock and vLLM backends with
  OpenAI-compatible chat completions, streaming SSE proxying, model aliases,
  weighted backend routing, fallback, API key auth, request IDs, structured
  JSON logging, and normalized errors.
- Added Redis-backed RPM, model-aware TPM, and concurrent request limiting,
  plus request body and chat input limits for operational safety.
- Implemented Prometheus/Grafana observability and alert rules for request
  volume, errors, rejection reasons, latency, streaming TTFT, streaming
  duration, and vLLM engine metrics.
- Created Docker Compose, Kubernetes, Helm, Argo CD, and Terraform deployment
  paths with optional ingress, HPA, external Secret references, vLLM startup
  probes, and a Gateway warmup tool.
- Benchmarked direct vLLM vs Gateway-routed streaming inference on a local RTX
  4060 Laptop GPU with p95/p99 latency, TTFT, inter-token latency, throughput,
  error-rate, and Prometheus snapshot/time-series evidence.
- Added CI, GHCR image publishing, Trivy and pip-audit security workflows,
  SBOM/provenance output, Dependabot updates, SemVer release validation, and a
  changelog-backed release process.

## Interview Talking Points

- Why a Gateway is still useful when vLLM already exposes an OpenAI-compatible
  API: stable client contract, auth, quotas, observability, and operational
  policy live outside model execution.
- Why the mock backend exists: reproducibility, CI coverage, and platform tests
  without CUDA or model downloads.
- Why benchmark TTFT and p95/p99 instead of only average latency: interactive
  chat UX and tail behavior are usually what users feel.
- Why token-aware TPM matters: quota and cost controls are not credible if they
  only count requests.
- Why GitOps/Terraform/security/release workflows are included: serving
  platforms are operated systems, not just inference scripts.

## Honest Limitations

- Local GPU validation uses `Qwen/Qwen2.5-0.5B-Instruct`; larger models require
  more available GPU memory and compatible driver/container versions.
- Kubernetes and Helm assets are deployment skeletons with practical production
  hooks, not a full managed inference platform or cloud cluster provisioner.
- The project does not implement multi-tenant billing, GPU cluster scheduling,
  cross-backend GPU-aware routing, LoRA adapter routing, incident response,
  SLA/SLO management, or enterprise identity integration.
- External RAG application integration is intentionally excluded from this
  completion, although the Gateway exposes the OpenAI-compatible interface that
  such an app would use.
