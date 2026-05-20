# Portfolio Demo Playbook

This demo is designed for a recruiter screen, portfolio review, or technical
interview. It shows the project as an LLM serving platform with a real
operational envelope: OpenAI-compatible API, FastAPI Gateway, vLLM GPU path,
Redis quotas, Prometheus/Grafana observability, benchmarks, Docker,
Kubernetes, Helm, GitOps, Terraform, and supply-chain automation.

## What High-Star Projects Usually Show

High-star AI infrastructure projects tend to make the first demo path very
short and concrete:

- vLLM leads with the serving value proposition, quickstart, documentation
  links, and performance claims.
- LiteLLM presents itself as an AI Gateway, then immediately explains the
  unified OpenAI-compatible interface, routing, logging, cost controls, and
  proxy deployment story.
- Open WebUI emphasizes visual proof with screenshots/GIFs, a short Docker
  quickstart, and clear integration targets such as Ollama and OpenAI-compatible
  APIs.

This repository should follow the same pattern: show one quick working path,
then expand into architecture, observability, benchmark evidence, and
deployment maturity.

## Demo Formats

| Format | Duration | Audience | Goal |
| --- | ---: | --- | --- |
| GitHub walkthrough | 60-90 seconds | recruiter | Show README, badges, benchmark table, docs, release, license, security policy |
| No-GPU live demo | 3-4 minutes | recruiter or junior technical screen | Prove the Gateway, mock backend, OpenAI SDK, streaming, and tests work locally |
| GPU/vLLM demo | 5-7 minutes | AI platform interviewer | Prove the same OpenAI-compatible contract routes to vLLM and produces benchmark/metrics evidence |
| Infra walkthrough | 3-5 minutes | MLOps/LLMOps interviewer | Show Docker, Kubernetes overlays, Helm, GitOps, Terraform, CI, Security, SBOM |

## One-Command Demo Controller

Print the complete walkthrough and command list:

```bash
uv run python scripts/demo_portfolio.py
```

Run the reproducible no-GPU live demo:

```bash
uv run python scripts/demo_portfolio.py --execute-local
```

This starts the mock backend and Gateway, waits for readiness, and runs the
OpenAI SDK smoke test against non-streaming and streaming chat completions.
The demo controller uses `18080` for the Gateway and `19000` for the mock
backend by default to avoid collisions with an already running Docker Compose
stack.

## 60-Second GitHub Walkthrough

1. Open the repository landing page.
2. Point out the title: `OpenAI-Compatible LLM Serving Gateway`.
3. Explain the badges: CI, Security, Release, Python, FastAPI, vLLM,
   Kubernetes/Helm, Observability.
4. Show the architecture diagram.
5. Show the benchmark snapshot and say it compares direct vLLM calls against
   Gateway-routed calls under the same prompt set and concurrency levels.
6. Open `docs/gateway_overhead_report.md` to show the detailed benchmark
   report.
7. Open `monitoring/grafana/dashboards` to show observability assets.
8. Open `deploy/helm`, `deploy/gitops`, and `deploy/terraform` to show
   production deployment paths.

Talk track:

```text
This project is not a model wrapper. It is the platform layer around model
serving: OpenAI-compatible Gateway, routing, quotas, observability, deployment
assets, benchmark evidence, and supply-chain automation.
```

## No-GPU Live Demo

Use this path when you cannot rely on CUDA, model downloads, or Docker GPU
runtime support.

```bash
uv sync --frozen --all-groups
uv run python scripts/demo_portfolio.py --execute-local
```

Expected evidence:

- Mock backend starts.
- Gateway starts.
- `/ready` passes.
- OpenAI SDK non-streaming request succeeds.
- OpenAI SDK streaming request succeeds.

What this proves:

- The project is reproducible without GPU.
- The Gateway implements the OpenAI-compatible client contract.
- The mock backend is useful for CI and demos.
- Streaming proxy behavior is testable without a real model server.

## GPU/vLLM Demo

Use this path when Docker can access an NVIDIA GPU.

```powershell
$env:VLLM_MODEL="Qwen/Qwen2.5-0.5B-Instruct"
$env:VLLM_IMAGE_TAG="v0.8.5.post1"
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

Warm up and smoke test:

```powershell
uv run python scripts/warmup_gateway.py --model qwen-small

$env:OPENAI_BASE_URL="http://localhost:8080/v1"
$env:OPENAI_API_KEY="dev-key"
$env:LLM_MODEL="qwen-small"
uv run python benchmark/client_smoke_test.py
```

What this proves:

- The same Gateway API can sit in front of vLLM.
- The `qwen-small` alias maps client-facing requests to the backend model.
- Streaming behavior works with a real GPU-backed model server.
- DCGM exporter and Prometheus are available in the GPU Compose path.

## Benchmark Demo

Run direct vLLM and Gateway-routed benchmarks with the same profile, prompt set,
streaming mode, and token limit.

Gateway run:

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

Collect metrics evidence:

```bash
uv run python benchmark/collect_prometheus_snapshot.py \
  --prometheus-url http://localhost:9090

uv run python benchmark/sample_prometheus_timeseries.py \
  --prometheus-url http://localhost:9090 \
  --duration-seconds 180 \
  --interval-seconds 5
```

What to say:

```text
The benchmark is not only average latency. It records RPS, p95/p99 latency,
TTFT, inter-token latency, TPOT, output events/sec, output tokens/sec when a
tokenizer is supplied, error rate, and Prometheus snapshots/time-series.
```

## Observability Demo

Open Grafana at:

```text
http://localhost:3000
```

Default credentials:

```text
admin / admin
```

Show:

- Gateway Overview: request rate, latency, errors, rejections, streaming TTFT.
- vLLM Engine Overview: running requests, waiting requests, KV cache pressure,
  prompt/generation tokens per second.
- GPU Overview: DCGM GPU utilization and framebuffer memory usage.

## Infra Demo

Render Kubernetes and Helm assets:

```bash
kubectl kustomize deploy/k8s
kubectl kustomize deploy/k8s-gpu

helm lint deploy/helm
helm template mini-llm deploy/helm \
  --namespace mini-llm-serving \
  --set vllm.enabled=true \
  --set mockBackend.enabled=false \
  --set dcgmExporter.enabled=true
```

Show:

- `deploy/k8s`: no-GPU baseline.
- `deploy/k8s-gpu`: vLLM and DCGM exporter overlay.
- `deploy/helm`: parameterized chart.
- `deploy/gitops`: Argo CD Applications.
- `deploy/terraform`: IaC entry point.
- `.github/workflows`: CI, Security, Container, Release workflows.

## Recording Storyboard

1. Repository landing page and one-sentence pitch.
2. Architecture diagram and feature table.
3. No-GPU demo command running successfully.
4. API call or OpenAI SDK smoke output.
5. GPU/vLLM Compose command and warmup result if available.
6. Benchmark report and Prometheus/Grafana evidence.
7. Helm/Kustomize render command.
8. CI/Security/Release workflows and GitHub Release page.
9. Close with honest scope boundaries: this is a production-style serving
   gateway, not a full enterprise GPU scheduler.

## What Not To Claim

Do not claim:

- Enterprise multi-tenant billing.
- GPU cluster autoscaling.
- LoRA adapter lifecycle management.
- Production incident response/SLO ownership.
- Managed cloud infrastructure provisioning.

Do claim:

- OpenAI-compatible Gateway layer.
- Reproducible no-GPU local path.
- Validated local vLLM GPU path.
- Redis-backed quotas and routing controls.
- Prometheus/Grafana/vLLM/DCGM observability.
- Benchmarking and release discipline.
- Docker, Kubernetes, Helm, GitOps, Terraform, CI, and supply-chain coverage.
