# Changelog

All notable changes to this project are documented here.

The project uses `vMAJOR.MINOR.PATCH` Git tags. Release tags must match the
`version` field in `pyproject.toml`.

## 0.1.2 - 2026-05-20

Portfolio polish and demo release:

- Renamed and polished the GitHub-facing project presentation for
  `llm-serving-gateway-vllm`, including README badges, clearer positioning,
  architecture overview, benchmark snapshot, and recruiter-oriented quickstart.
- Added MIT license metadata and a GitHub security policy so the repository has
  explicit portfolio-ready license and vulnerability reporting surfaces.
- Cleaned deployment secret placeholders in Kubernetes and Helm manifests so
  production templates no longer advertise local demo credentials.
- Added a reproducible portfolio demo walkthrough with no-GPU mock execution,
  GPU/vLLM demo commands, benchmark commands, and talking points for interviews.
- Added tests that keep README, demo documentation, license, security policy,
  and deployment secret placeholders aligned.

## 0.1.1 - 2026-05-20

Portfolio benchmark and GPU observability release:

- Added tokenizer-level benchmark output token counts, output token/s, and TPOT
  when a Hugging Face `tokenizer.json` is supplied.
- Added DCGM exporter wiring for Docker GPU mode, Kubernetes GPU overlay, Helm,
  and GitOps/Terraform values.
- Added GPU Prometheus queries and a Grafana `GPU Overview` dashboard for GPU
  utilization and framebuffer memory.
- Updated benchmark reports and documentation to distinguish SSE output chunks
  from tokenizer-level output tokens.
- Included the Security workflow fixes made after `v0.1.0` so the formal
  release tag contains the passing CI, container, and security workflow state.

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
