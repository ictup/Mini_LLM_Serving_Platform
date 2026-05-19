# Changelog

All notable changes to this project are documented here.

The project uses `vMAJOR.MINOR.PATCH` Git tags. Release tags must match the
`version` field in `pyproject.toml`.

## 0.1.0 - 2026-05-19

Initial portfolio release:

- OpenAI-compatible FastAPI Gateway with `/v1/models` and
  `/v1/chat/completions`.
- Streaming SSE proxy with TTFT and stream-duration metrics.
- Mock backend and locally validated vLLM GPU backend path.
- Redis-backed RPM, TPM, and concurrency limits.
- Model-aware token accounting and weighted model routing with fallback.
- Benchmark runner, direct-vs-Gateway comparison report, and Prometheus metric
  snapshot/time-series collectors.
- Prometheus metrics, Grafana dashboards, and alert rules.
- Docker Compose, Kubernetes overlays, Helm chart, Argo CD GitOps examples, and
  Terraform IaC skeleton.
- CI, container image publishing, supply-chain security workflow, Dependabot,
  SBOM/provenance support, and production hardening documentation.
