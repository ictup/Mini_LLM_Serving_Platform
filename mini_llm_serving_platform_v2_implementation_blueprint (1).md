# Mini LLM Serving Platform with vLLM — V2 Implementation Blueprint

> **Goal**: Build a production-style OpenAI-compatible LLM serving gateway that can be fully reproduced locally without GPU using a mock backend, and can switch to vLLM when GPU is available.  
> **Target roles**: Junior AI Engineer / GenAI Backend Engineer / Applied LLM Engineer / MLOps Engineer / AI Infrastructure-adjacent Engineer  
> **Repository name**: `mini-llm-serving-platform`  
> **CV project name**: `OpenAI-Compatible LLM Serving Platform with vLLM`  
> **Positioning**: production-style portfolio project, not a full enterprise inference platform.

---

## 0. What This Project Should Prove

This project should prove that you understand the **LLM serving layer**, not just the application layer.

It should demonstrate:

1. How to serve an LLM behind an **OpenAI-compatible API**.
2. Why a production team may place a **gateway in front of vLLM**.
3. How to implement **streaming and non-streaming** chat completions.
4. How to add **API key authentication**, **request IDs**, and **structured logging**.
5. How to implement **Redis-backed rate limiting**.
6. How to expose **Prometheus metrics** and visualize them in **Grafana**.
7. How to run **benchmarks** for latency, TTFT, TPOT, throughput, and gateway overhead.
8. How to provide a **no-GPU mock backend** for local development and reproducible demos.
9. How to switch to a real **vLLM backend** when GPU is available.
10. How to integrate with your **Production RAG Assistant** as a drop-in OpenAI-compatible backend.

---

## 1. One-Sentence Project Description

Build a production-style OpenAI-compatible LLM serving platform with a FastAPI gateway in front of vLLM, featuring streaming inference, model aliases, API key authentication, Redis-backed rate limiting, Prometheus/Grafana observability, structured logging, direct-vLLM vs gateway benchmark reports, Docker Compose, optional Kubernetes/Helm templates, and RAG application integration.

---

## 2. Why This Is Not Just “Running vLLM”

A weak project:

```text
vllm serve model_name
curl /v1/chat/completions
```

A strong portfolio project:

```text
OpenAI-compatible client
→ FastAPI gateway
→ auth / request ID / rate limit / logging / metrics / routing
→ vLLM OpenAI-compatible backend
→ local LLM model
→ benchmark + observability + RAG integration
```

The project should show that you understand why internal platforms often avoid exposing raw model servers directly:

```text
client stability
auth
rate limiting
observability
model aliasing
backend switching
error normalization
benchmarking
integration with LLM apps
```

---

## 3. Scope

### 3.1 MVP Scope

Complete this first:

```text
[ ] FastAPI gateway starts locally.
[ ] Mock backend starts locally without GPU.
[ ] /v1/chat/completions supports stream=false.
[ ] /v1/chat/completions supports stream=true with SSE.
[ ] OpenAI Python SDK can call the gateway.
[ ] API key authentication works.
[ ] /health and /ready work.
[ ] /metrics exposes Prometheus metrics.
[ ] Docker Compose starts gateway + mock backend + Redis + Prometheus + Grafana.
[ ] Benchmark script outputs p50/p95 latency and RPS for mock backend.
[ ] README contains architecture, quickstart, API example, and limitations.
```

### 3.2 Job-Ready Scope

For CV use, complete:

```text
[ ] vLLM backend can be enabled when GPU is available.
[ ] Gateway supports model aliases.
[ ] Redis-backed per-key rate limiting.
[ ] Request ID propagation.
[ ] Structured JSON logging.
[ ] Streaming proxy measures TTFT.
[ ] Benchmark compares direct backend vs gateway-routed path.
[ ] Benchmark report includes TTFT, TPOT, ITL, E2E latency, output tokens/sec, RPS, error rate.
[ ] Prometheus + Grafana dashboard.
[ ] OpenAI SDK smoke test.
[ ] RAG integration smoke test.
[ ] GitHub Actions CI.
[ ] docs/design_decisions.md.
[ ] docs/benchmark_report.md.
[ ] docs/failure_analysis.md.
```

### 3.3 Strong Portfolio Scope

Optional:

```text
[ ] Kubernetes manifests.
[ ] Minimal Helm chart.
[ ] Canary routing design.
[ ] Multi-backend interface: vLLM + mock + optional TGI/SGLang note.
[ ] Per-model metrics.
[ ] Optional gateway-to-vLLM health propagation.
[ ] Optional token-based TPM rate limiting.
```

---

## 4. Non-Goals

Do not overbuild:

```text
[ ] No full multi-tenant billing system.
[ ] No enterprise user management UI.
[ ] No production GPU scheduler.
[ ] No autoscaling requirement in MVP.
[ ] No distributed multi-node vLLM deployment as a core feature.
[ ] No LoRA adapter routing as a core feature.
[ ] No SLA/SLO guarantees.
[ ] No incident response system.
```

Interview explanation:

> I intentionally scoped this as a production-style LLM serving gateway rather than a full enterprise inference platform. The goal is to demonstrate API compatibility, streaming, auth, rate limiting, metrics, benchmarks, deployment, and RAG integration.

---

## 5. Technology Stack

| Layer | Choice | Why |
|---|---|---|
| LLM backend | vLLM | High-throughput LLM serving with OpenAI-compatible API |
| Gateway | FastAPI | Typed API, async proxy, testing, middleware |
| HTTP proxy | httpx | Async non-streaming and streaming proxy |
| Schemas | Pydantic v2 | OpenAI-style request/response validation |
| Mock backend | FastAPI | Reproducible no-GPU development |
| Auth | Bearer API key | Minimal platform boundary |
| Rate limit | Redis | Shared per-key rate limiting |
| Metrics | prometheus-client | Gateway metrics exposed at `/metrics` |
| Monitoring | Prometheus + Grafana | Time-series metrics and dashboard |
| Logging | structlog | JSON structured logs |
| Benchmark | async Python runner + optional Locust | Latency and throughput testing |
| Deployment | Docker Compose | Local reproducibility |
| Optional deployment | Kubernetes + Helm | Infra signal without overbuilding |
| CI | GitHub Actions | lint/test/build |

---

## 6. Metrics You Must Understand

These definitions are important for interviews.

### 6.1 TTFT: Time To First Token

```text
Time from sending request to receiving first generated token.
```

Why it matters:

```text
Most important user-perceived latency metric for streaming.
```

### 6.2 E2E Latency: End-to-End Latency

```text
Time from sending request to receiving the final token / full response.
```

Why it matters:

```text
Represents total waiting time for non-streaming clients.
```

### 6.3 TPOT: Time Per Output Token

```text
Average time needed to generate each output token after the first token.
```

Why it matters:

```text
Measures decode speed.
```

### 6.4 ITL: Inter-Token Latency

```text
Time gap between consecutive streamed tokens.
```

Why it matters:

```text
Measures smoothness of streaming experience.
```

### 6.5 Output Tokens/sec

```text
Number of generated output tokens per second.
```

Why it matters:

```text
Core throughput metric for LLM serving.
```

### 6.6 RPS: Requests Per Second

```text
Completed requests per second.
```

Why it matters:

```text
Measures request throughput under concurrency.
```

### 6.7 Gateway Overhead

```text
gateway-routed latency - direct backend latency
```

Why it matters:

```text
Shows the cost of auth, logging, rate limiting, metrics, and proxy logic.
```

---

## 7. Architecture

```text
                    ┌────────────────────────────┐
                    │          Client             │
                    │ OpenAI SDK / curl / RAG app │
                    └──────────────┬─────────────┘
                                   │
                                   ▼
                    ┌────────────────────────────┐
                    │      FastAPI Gateway        │
                    │ /v1/chat/completions        │
                    │ /v1/models                  │
                    │ /health /ready /metrics     │
                    └──────────────┬─────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                          │
        ▼                          ▼                          ▼
┌─────────────────┐      ┌────────────────────┐      ┌────────────────────┐
│ Auth / Rate      │      │ Metrics / Logging   │      │ Routing / Proxy     │
│ Bearer key       │      │ Prometheus          │      │ model aliases       │
│ Redis RPM/TPM    │      │ structlog JSON      │      │ streaming proxy     │
└─────────────────┘      └────────────────────┘      └─────────┬──────────┘
                                                                │
                                                                ▼
                                            ┌────────────────────────────┐
                                            │      Backend Selector       │
                                            │ mock / vLLM / future TGI    │
                                            └──────────────┬─────────────┘
                                                           │
                            ┌──────────────────────────────┼──────────────────────────────┐
                            │                              │                              │
                            ▼                              ▼                              ▼
              ┌──────────────────────┐       ┌──────────────────────┐       ┌──────────────────────┐
              │ Mock Backend          │       │ vLLM Server           │       │ Future Backend        │
              │ no GPU demo           │       │ OpenAI-compatible API │       │ SGLang / TGI          │
              └──────────────────────┘       └──────────────────────┘       └──────────────────────┘

                    ┌────────────────────────────┐
                    │ Prometheus + Grafana        │
                    │ gateway + backend metrics   │
                    └────────────────────────────┘
```

---

## 8. Gateway Metrics vs vLLM Engine Metrics

You should be able to explain this clearly.

### 8.1 Gateway Metrics

Gateway metrics answer:

```text
How does the API platform behave from the client's perspective?
```

Examples:

```text
gateway request count
gateway error count
auth failures
rate-limited requests
gateway latency
TTFT observed by gateway
backend timeout count
requests by model alias
requests by backend
```

### 8.2 vLLM Engine Metrics

vLLM metrics answer:

```text
What happens inside the inference engine?
```

Examples:

```text
queueing
scheduler behavior
KV cache usage
prefill/decode behavior
token throughput
engine-level latency
running/waiting requests
```

### 8.3 Interview Answer

> Gateway metrics tell me user-facing API behavior, while vLLM metrics tell me engine-level behavior. If p95 latency is high, gateway metrics show whether it is due to auth, rate limiting, proxy timeout, or client-facing latency. vLLM metrics help identify whether the backend is queueing, memory-bound, or decode-bound.

---

## 9. Repository Structure

```text
mini-llm-serving-platform/
  README.md
  PROJECT_SPEC.md
  IMPLEMENTATION_PLAN.md
  Makefile
  pyproject.toml
  uv.lock
  .env.example
  .gitignore

  docker-compose.yml
  docker-compose.gpu.yml
  Dockerfile.gateway

  gateway/
    app/
      __init__.py
      main.py

      api/
        __init__.py
        routes_chat.py
        routes_models.py
        routes_health.py
        routes_metrics.py

      core/
        __init__.py
        config.py
        logging.py
        errors.py
        security.py
        rate_limit.py
        request_id.py

      proxy/
        __init__.py
        backend_client.py
        streaming.py
        router.py
        model_aliases.py

      observability/
        __init__.py
        metrics.py
        tracing.py

      schemas/
        __init__.py
        openai.py
        errors.py
        health.py
        metrics.py

    tests/
      test_health.py
      test_auth.py
      test_rate_limit.py
      test_request_id.py
      test_chat_proxy.py
      test_streaming.py
      test_models.py
      test_metrics.py
      test_error_mapping.py

  serving/
    mock_backend/
      app.py
      Dockerfile
    vllm/
      README.md
      run_vllm.sh
      docker-compose.vllm.yml

  benchmark/
    prompts/
      short_prompts.jsonl
      long_prompts.jsonl
      coding_prompts.jsonl
    client_smoke_test.py
    rag_integration_smoke_test.py
    run_benchmark.py
    run_locust.py
    locustfile.py
    analyze_results.py
    results/

  monitoring/
    prometheus/
      prometheus.yml
    grafana/
      dashboards/
        llm-serving-dashboard.json
      provisioning/
        datasources/
        dashboards/

  deploy/
    k8s/
      gateway-deployment.yaml
      gateway-service.yaml
      vllm-deployment.yaml
      vllm-service.yaml
      redis-deployment.yaml
      redis-service.yaml
    helm/
      Chart.yaml
      values.yaml
      templates/

  docs/
    architecture.md
    api_contract.md
    benchmark_report.md
    design_decisions.md
    failure_analysis.md
    production_checklist.md
    rag_integration.md
    screenshots/
```

---

## 10. Environment Setup

### 10.1 Create Project

```bash
mkdir mini-llm-serving-platform
cd mini-llm-serving-platform
git init
uv init
```

### 10.2 Dependencies

```bash
uv add fastapi uvicorn pydantic pydantic-settings
uv add httpx structlog prometheus-client redis tenacity python-dotenv
uv add openai
uv add numpy pandas rich
uv add pytest pytest-asyncio pytest-cov ruff mypy pre-commit --dev
```

Optional load testing:

```bash
uv add locust --dev
```

Optional GPU serving:

```bash
uv add vllm
```

In many cases, vLLM is better installed in the vLLM container rather than the gateway environment.

---

## 11. `.env.example`

```env
APP_NAME=mini-llm-serving-platform
ENV=local
LOG_LEVEL=INFO
LOG_PROMPTS=false

GATEWAY_HOST=0.0.0.0
GATEWAY_PORT=8080

API_KEYS=dev-key,team-a-key
RATE_LIMIT_ENABLED=true
RATE_LIMIT_RPM=60
RATE_LIMIT_TPM=20000

REDIS_URL=redis://localhost:6379/0

BACKEND_TYPE=mock
MOCK_BASE_URL=http://localhost:9000/v1

VLLM_BASE_URL=http://localhost:8000/v1
VLLM_API_KEY=local-vllm-key

DEFAULT_MODEL=mock
MODEL_ALIASES_JSON={"mock":"mock","qwen-small":"Qwen/Qwen2.5-1.5B-Instruct"}

BACKEND_TIMEOUT_SECONDS=120
STREAMING_TIMEOUT_SECONDS=300

METRICS_ENABLED=true
```

---

## 12. OpenAI-Compatible API Contract

### 12.1 `POST /v1/chat/completions`

Request:

```json
{
  "model": "qwen-small",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Explain KV cache in two sentences."}
  ],
  "temperature": 0.2,
  "top_p": 0.95,
  "max_tokens": 256,
  "stream": false
}
```

Non-streaming response:

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1710000000,
  "model": "qwen-small",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "KV cache stores previously computed key and value tensors..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 42,
    "completion_tokens": 38,
    "total_tokens": 80
  }
}
```

Streaming response:

```text
data: {"id":"chatcmpl-...","object":"chat.completion.chunk","choices":[{"delta":{"content":"KV"}}]}

data: {"id":"chatcmpl-...","object":"chat.completion.chunk","choices":[{"delta":{"content":" cache"}}]}

data: [DONE]
```

### 12.2 `GET /v1/models`

Response:

```json
{
  "object": "list",
  "data": [
    {
      "id": "qwen-small",
      "object": "model",
      "owned_by": "gateway"
    }
  ]
}
```

### 12.3 `GET /health`

```json
{"status": "ok"}
```

### 12.4 `GET /ready`

```json
{
  "status": "ready",
  "backend": "ok",
  "redis": "ok",
  "models": "ok"
}
```

### 12.5 `GET /metrics`

Prometheus exposition format.

---

## 13. OpenAI-Compatible Schemas

`gateway/app/schemas/openai.py`

```python
from typing import Literal, Any
from pydantic import BaseModel, Field

class Message(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[Message]
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    stream: bool = False
    stop: str | list[str] | None = None
    user: str | None = None

class ChatCompletionChoice(BaseModel):
    index: int
    message: Message
    finish_reason: str | None = None

class Usage(BaseModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]
    usage: Usage | None = None
```

Do not aim to implement the full OpenAI API surface. Implement enough for:

```text
OpenAI Python SDK
LiteLLM
your RAG assistant
curl
```

---

## 14. Error Format

Use OpenAI-style errors.

### 14.1 401 Authentication Error

```json
{
  "error": {
    "message": "invalid api key",
    "type": "authentication_error",
    "code": "invalid_api_key"
  },
  "request_id": "req_..."
}
```

### 14.2 429 Rate Limit Error

```json
{
  "error": {
    "message": "rate limit exceeded",
    "type": "rate_limit_error",
    "code": "rate_limit_exceeded"
  },
  "request_id": "req_..."
}
```

### 14.3 502 Backend Error

```json
{
  "error": {
    "message": "model backend unavailable",
    "type": "backend_error",
    "code": "backend_unavailable"
  },
  "request_id": "req_..."
}
```

### 14.4 504 Backend Timeout

```json
{
  "error": {
    "message": "model backend timed out",
    "type": "timeout_error",
    "code": "backend_timeout"
  },
  "request_id": "req_..."
}
```

Rules:

```text
[ ] every error has request_id
[ ] no backend secrets in response
[ ] no raw prompt in error message
[ ] errors increment Prometheus counters
```

---

## 15. Phase 1 — Gateway Skeleton and Mock Backend

### 15.1 FastAPI Skeleton

Files:

```text
gateway/app/main.py
gateway/app/api/routes_health.py
gateway/app/core/config.py
```

Endpoints:

```text
GET /health
GET /ready
```

### 15.2 Mock Backend

Files:

```text
serving/mock_backend/app.py
serving/mock_backend/Dockerfile
```

Mock endpoints:

```text
GET /v1/models
POST /v1/chat/completions
```

Non-streaming behavior:

```text
return deterministic JSON response
```

Streaming behavior:

```text
yield SSE chunks with small delay
```

Example mock streaming:

```python
async def stream_response():
    for token in ["Hello", " from", " mock", " backend"]:
        yield f'data: {{"choices":[{{"delta":{{"content":"{token}"}}}}]}}\n\n'
        await asyncio.sleep(0.05)
    yield "data: [DONE]\n\n"
```

### 15.3 Acceptance

```bash
make dev
make mock
curl http://localhost:8080/health
curl http://localhost:9000/v1/models
```

---

## 16. Phase 2 — Gateway Proxy

### 16.1 Backend Client

`gateway/app/proxy/backend_client.py`

Responsibilities:

```text
[ ] map model alias to backend model name
[ ] forward headers safely
[ ] forward JSON body
[ ] handle timeout
[ ] handle backend connection error
[ ] return OpenAI-style errors
```

### 16.2 Non-Streaming Proxy

Flow:

```text
client request
→ validate OpenAI-style schema
→ authenticate
→ rate limit
→ add request_id
→ map model alias
→ forward to backend
→ return backend JSON
→ record metrics and logs
```

### 16.3 Streaming Proxy

Flow:

```text
client stream=true
→ authenticate and rate limit
→ send streaming request to backend
→ measure TTFT when first non-empty chunk arrives
→ yield SSE chunks to client
→ record E2E latency and metrics
```

### 16.4 Acceptance

```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-key" \
  -d '{"model":"mock","messages":[{"role":"user","content":"hello"}],"stream":false}'
```

Streaming:

```bash
curl -N -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-key" \
  -d '{"model":"mock","messages":[{"role":"user","content":"hello"}],"stream":true}'
```

---

## 17. Phase 3 — Auth, Request ID, Rate Limiting, Logging

### 17.1 API Key Auth

Header:

```http
Authorization: Bearer dev-key
```

Rules:

```text
missing key → 401
wrong key → 401
correct key → continue
do not log raw API key
```

Store safe hash prefix only:

```python
import hashlib

def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()[:8]
```

### 17.2 Request ID

Header:

```http
X-Request-ID: optional-client-request-id
```

If missing:

```text
generate req_<uuid>
```

Return:

```http
X-Request-ID: req_...
```

### 17.3 Redis RPM Rate Limiting

MVP:

```text
per API key requests per minute
```

Algorithm:

```text
INCR key:{api_key_hash}:{current_minute}
EXPIRE 60 seconds
if count > RATE_LIMIT_RPM → 429
```

### 17.4 Optional TPM Rate Limiting

Job-ready optional:

```text
estimate prompt tokens before request
add completion tokens after response
limit total tokens per minute
```

Do not overcomplicate MVP.

### 17.5 Structured Logging

Use `structlog`.

Log fields:

```text
timestamp
level
request_id
api_key_hash
model
backend
stream
status_code
latency_ms
ttft_ms
prompt_tokens
completion_tokens
error_type
```

Do not log by default:

```text
raw API key
raw prompt
raw response
authorization header
```

---

## 18. Phase 4 — Prometheus Metrics

### 18.1 Required Metrics

```text
llm_gateway_requests_total
llm_gateway_errors_total
llm_gateway_request_latency_seconds
llm_gateway_streaming_requests_total
llm_gateway_time_to_first_token_seconds
llm_gateway_tokens_in_total
llm_gateway_tokens_out_total
llm_gateway_rate_limited_total
llm_gateway_backend_timeouts_total
```

### 18.2 Example Implementation

```python
from prometheus_client import Counter, Histogram

REQUESTS_TOTAL = Counter(
    "llm_gateway_requests_total",
    "Total gateway requests",
    ["model", "backend", "status_code", "stream"],
)

REQUEST_LATENCY = Histogram(
    "llm_gateway_request_latency_seconds",
    "End-to-end gateway request latency",
    ["model", "backend", "stream"],
)

TTFT = Histogram(
    "llm_gateway_time_to_first_token_seconds",
    "Time to first token for streaming requests",
    ["model", "backend"],
)

ERRORS_TOTAL = Counter(
    "llm_gateway_errors_total",
    "Total gateway errors",
    ["error_type", "backend"],
)
```

### 18.3 Safe Labels

Allowed:

```text
model
backend
status_code
stream
error_type
```

Avoid:

```text
request_id
raw prompt
user_id
api key
full URL
random IDs
```

### 18.4 `/metrics`

Expose:

```text
GET /metrics
```

---

## 19. Phase 5 — vLLM Backend

### 19.1 Model Choices

For small GPU:

```text
Qwen/Qwen2.5-1.5B-Instruct
Qwen/Qwen2.5-3B-Instruct
meta-llama/Llama-3.2-3B-Instruct
```

For stronger GPU:

```text
mistralai/Mistral-7B-Instruct-v0.3
Qwen/Qwen2.5-7B-Instruct
```

If no GPU:

```text
Use mock backend and document GPU path.
```

### 19.2 Run Script

`serving/vllm/run_vllm.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

MODEL=${MODEL:-Qwen/Qwen2.5-1.5B-Instruct}
PORT=${PORT:-8000}
API_KEY=${VLLM_API_KEY:-local-vllm-key}

vllm serve "$MODEL" \
  --host 0.0.0.0 \
  --port "$PORT" \
  --api-key "$API_KEY" \
  --dtype auto \
  --generation-config vllm \
  --disable-log-requests
```

### 19.3 Gateway Config

```env
BACKEND_TYPE=vllm
VLLM_BASE_URL=http://localhost:8000/v1
VLLM_API_KEY=local-vllm-key
MODEL_ALIASES_JSON={"qwen-small":"Qwen/Qwen2.5-1.5B-Instruct"}
```

### 19.4 Direct vLLM Test

```bash
curl http://localhost:8000/v1/models \
  -H "Authorization: Bearer local-vllm-key"
```

### 19.5 Gateway to vLLM Test

```bash
curl http://localhost:8080/v1/models \
  -H "Authorization: Bearer dev-key"
```

---

## 20. Phase 6 — Model Aliases

### 20.1 Why Model Aliases?

Clients should use stable names:

```text
qwen-small
mistral-small
default-chat
```

Backend may use long Hugging Face IDs:

```text
Qwen/Qwen2.5-1.5B-Instruct
mistralai/Mistral-7B-Instruct-v0.3
```

### 20.2 Alias Mapping

`.env`:

```env
MODEL_ALIASES_JSON={"mock":"mock","qwen-small":"Qwen/Qwen2.5-1.5B-Instruct"}
```

### 20.3 Router Logic

```python
def resolve_model_alias(model: str) -> str:
    return settings.model_aliases.get(model, model)
```

### 20.4 Interview Answer

> Model aliases decouple client-facing names from backend model IDs. This makes it easier to migrate models, run canaries, or switch providers without changing clients.

---

## 21. Phase 7 — Benchmark Suite

### 21.1 Prompt Datasets

`benchmark/prompts/short_prompts.jsonl`

```json
{"id":"short_001","prompt":"Explain KV cache in two sentences.","max_tokens":128}
{"id":"short_002","prompt":"What is TTFT in LLM serving?","max_tokens":128}
```

`benchmark/prompts/long_prompts.jsonl`

```json
{"id":"long_001","prompt":"Explain how PagedAttention improves LLM serving memory efficiency.","max_tokens":512}
```

`benchmark/prompts/coding_prompts.jsonl`

```json
{"id":"code_001","prompt":"Write a Python function that implements a simple token bucket rate limiter.","max_tokens":512}
```

### 21.2 Benchmark CLI

```bash
uv run python benchmark/run_benchmark.py \
  --base-url http://localhost:8080/v1 \
  --api-key dev-key \
  --model qwen-small \
  --prompts benchmark/prompts/short_prompts.jsonl \
  --concurrency 1 2 4 8 16 \
  --requests-per-level 50 \
  --stream true
```

### 21.3 Metrics to Record

```text
request_count
success_count
error_count
p50_latency
p95_latency
p99_latency
p50_ttft
p95_ttft
mean_tpot
mean_itl
tokens_per_second
requests_per_second
avg_prompt_tokens
avg_completion_tokens
gateway_overhead
```

### 21.4 Direct Backend vs Gateway

Run both:

```bash
# Direct backend
uv run python benchmark/run_benchmark.py \
  --base-url http://localhost:8000/v1 \
  --api-key local-vllm-key \
  --model Qwen/Qwen2.5-1.5B-Instruct \
  --prompts benchmark/prompts/short_prompts.jsonl \
  --concurrency 1 2 4 8 \
  --stream true

# Gateway
uv run python benchmark/run_benchmark.py \
  --base-url http://localhost:8080/v1 \
  --api-key dev-key \
  --model qwen-small \
  --prompts benchmark/prompts/short_prompts.jsonl \
  --concurrency 1 2 4 8 \
  --stream true
```

### 21.5 Benchmark Report Template

`docs/benchmark_report.md`

```markdown
# LLM Serving Benchmark Report

## Setup

| Item | Value |
|---|---|
| Backend | vLLM |
| Gateway | FastAPI |
| Model | Qwen/Qwen2.5-1.5B-Instruct |
| GPU | ... |
| Precision | auto |
| Prompt set | short / long / coding |
| Concurrency | 1, 2, 4, 8, 16 |
| Streaming | true / false |

## Direct vLLM vs Gateway

| Path | P50 Latency | P95 Latency | P50 TTFT | P95 TTFT | Output tok/s | Error Rate |
|---|---:|---:|---:|---:|---:|---:|
| direct vLLM | ... | ... | ... | ... | ... | ... |
| gateway → vLLM | ... | ... | ... | ... | ... | ... |
| overhead | ... | ... | ... | ... | ... | ... |

## Concurrency Scaling

| Concurrency | RPS | P50 Latency | P95 Latency | P50 TTFT | Output tok/s | Error Rate |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | ... | ... | ... | ... | ... | ... |
| 2 | ... | ... | ... | ... | ... | ... |
| 4 | ... | ... | ... | ... | ... | ... |
| 8 | ... | ... | ... | ... | ... | ... |
| 16 | ... | ... | ... | ... | ... | ... |

## Streaming vs Non-Streaming

| Mode | P50 TTFT | P95 E2E Latency | Output tok/s |
|---|---:|---:|---:|
| streaming | ... | ... | ... |
| non-streaming | N/A | ... | ... |

## Findings

- Gateway overhead:
- Main bottleneck:
- Recommended concurrency:
- Failure cases:
```

---

## 22. Phase 8 — Prometheus and Grafana

### 22.1 Prometheus Config

`monitoring/prometheus/prometheus.yml`

```yaml
global:
  scrape_interval: 5s

scrape_configs:
  - job_name: "llm-gateway"
    static_configs:
      - targets: ["gateway:8080"]

  - job_name: "mock-backend"
    static_configs:
      - targets: ["mock-backend:9000"]

  - job_name: "vllm"
    static_configs:
      - targets: ["vllm:8000"]
```

If vLLM is not enabled, Prometheus may show that target as down. That is acceptable for no-GPU mode if documented.

### 22.2 Grafana Panels

Create dashboard panels:

```text
1. Requests per minute
2. Error rate
3. P50 latency
4. P95 latency
5. P99 latency
6. P50 TTFT
7. P95 TTFT
8. Output tokens/sec
9. Rate-limited requests
10. Backend timeouts
11. Requests by model
12. Requests by backend
```

### 22.3 Acceptance

```text
[ ] Run benchmark.
[ ] Open Grafana.
[ ] Dashboard panels update.
[ ] README includes screenshot.
```

---

## 23. Phase 9 — Docker Compose

### 23.1 No-GPU Default Stack

`docker-compose.yml`

Services:

```text
gateway
mock-backend
redis
prometheus
grafana
```

Example:

```yaml
services:
  gateway:
    build:
      context: .
      dockerfile: Dockerfile.gateway
    ports:
      - "8080:8080"
    env_file:
      - .env
    depends_on:
      - redis
      - mock-backend

  mock-backend:
    build:
      context: .
      dockerfile: serving/mock_backend/Dockerfile
    ports:
      - "9000:9000"

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  prometheus:
    image: prom/prometheus
    volumes:
      - ./monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    volumes:
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
      - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards
```

### 23.2 GPU Stack

`docker-compose.gpu.yml`

Services:

```text
vllm
gateway configured with BACKEND_TYPE=vllm
```

Example:

```yaml
services:
  vllm:
    image: vllm/vllm-openai:latest
    runtime: nvidia
    environment:
      - HUGGING_FACE_HUB_TOKEN=${HUGGING_FACE_HUB_TOKEN}
    command: >
      --model Qwen/Qwen2.5-1.5B-Instruct
      --host 0.0.0.0
      --port 8000
      --api-key local-vllm-key
      --dtype auto
      --disable-log-requests
    ports:
      - "8000:8000"
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: ["gpu"]
```

Run no-GPU:

```bash
docker compose up --build
```

Run GPU:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

---

## 24. Phase 10 — OpenAI SDK Smoke Test

`benchmark/client_smoke_test.py`

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="dev-key",
)

response = client.chat.completions.create(
    model="mock",
    messages=[{"role": "user", "content": "Say hello in one sentence."}],
)

print(response.choices[0].message.content)
```

Streaming:

```python
stream = client.chat.completions.create(
    model="mock",
    messages=[{"role": "user", "content": "Count to five."}],
    stream=True,
)

for chunk in stream:
    delta = chunk.choices[0].delta.content
    if delta:
        print(delta, end="", flush=True)
```

Acceptance:

```bash
uv run python benchmark/client_smoke_test.py
```

---

## 25. Phase 11 — RAG Integration

### 25.1 Purpose

This project becomes much stronger when it is connected to your RAG project:

```text
Production RAG Assistant
→ LiteLLM / OpenAI SDK
→ Mini LLM Serving Gateway
→ vLLM or mock backend
```

### 25.2 RAG Environment Variables

In your RAG project:

```env
OPENAI_BASE_URL=http://localhost:8080/v1
OPENAI_API_KEY=dev-key
LLM_MODEL=mock
```

With GPU:

```env
OPENAI_BASE_URL=http://localhost:8080/v1
OPENAI_API_KEY=dev-key
LLM_MODEL=qwen-small
```

### 25.3 RAG Integration Smoke Test

`benchmark/rag_integration_smoke_test.py`

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="dev-key",
)

response = client.chat.completions.create(
    model="mock",
    messages=[
        {"role": "system", "content": "You answer using retrieved context."},
        {"role": "user", "content": "Context: KV cache stores previous keys and values. Question: What is KV cache?"}
    ],
)

print(response.choices[0].message.content)
```

### 25.4 README Sentence

Add:

```text
This serving gateway can be used as a drop-in OpenAI-compatible backend for my Production RAG Assistant by setting OPENAI_BASE_URL to the gateway URL.
```

---

## 26. Phase 12 — Kubernetes and Helm Optional

Do this only after MVP is complete.

### 26.1 Kubernetes Manifests

Files:

```text
deploy/k8s/gateway-deployment.yaml
deploy/k8s/gateway-service.yaml
deploy/k8s/vllm-deployment.yaml
deploy/k8s/vllm-service.yaml
deploy/k8s/redis-deployment.yaml
deploy/k8s/redis-service.yaml
```

Gateway:

```text
livenessProbe: /health
readinessProbe: /ready
```

vLLM:

```yaml
resources:
  limits:
    nvidia.com/gpu: 1
```

### 26.2 Helm Chart

Files:

```text
deploy/helm/Chart.yaml
deploy/helm/values.yaml
deploy/helm/templates/
```

`values.yaml`:

```yaml
gateway:
  replicas: 1
  image: mini-llm-gateway:latest

vllm:
  enabled: true
  model: Qwen/Qwen2.5-1.5B-Instruct
  gpu: 1

redis:
  enabled: true

monitoring:
  serviceMonitor:
    enabled: false
```

---

## 27. Engine Comparison: vLLM vs SGLang vs TGI

This section goes in README or `docs/design_decisions.md`.

| Engine | Why relevant | Why not primary in this project |
|---|---|---|
| vLLM | Mature OpenAI-compatible serving, strong throughput, widely used, Prometheus metrics | Primary backend |
| SGLang | Strong production serving framework, OpenAI-compatible APIs, good for structured/agentic workloads | Future comparison |
| TGI | Production-ready server with Prometheus, OpenTelemetry, SSE streaming, continuous batching | Reference only |
| TensorRT-LLM | Very high performance on NVIDIA stack | Too hardware-specific for junior portfolio MVP |

Interview answer:

> I chose vLLM because it is widely used, OpenAI-compatible, and easy to integrate with my RAG application. I documented SGLang and TGI as references because they represent alternative production inference stacks, but implementing all of them would dilute the project.

---

## 28. Makefile

```makefile
.PHONY: dev test lint format mock benchmark smoke docker-up docker-down

dev:
	uv run uvicorn gateway.app.main:app --reload --host 0.0.0.0 --port 8080

mock:
	uv run uvicorn serving.mock_backend.app:app --reload --host 0.0.0.0 --port 9000

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

smoke:
	uv run python benchmark/client_smoke_test.py

benchmark:
	uv run python benchmark/run_benchmark.py \
		--base-url http://localhost:8080/v1 \
		--api-key dev-key \
		--model mock \
		--prompts benchmark/prompts/short_prompts.jsonl \
		--concurrency 1 2 4 8 \
		--requests-per-level 20 \
		--stream true

docker-up:
	docker compose up --build

docker-down:
	docker compose down
```

---

## 29. GitHub Actions

`.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  gateway:
    runs-on: ubuntu-latest

    services:
      redis:
        image: redis:7
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Set up Python
        run: uv python install 3.11

      - name: Install dependencies
        run: uv sync

      - name: Lint
        run: uv run ruff check .

      - name: Test
        run: uv run pytest
        env:
          API_KEYS: dev-key
          REDIS_URL: redis://localhost:6379/0
          BACKEND_TYPE: mock
          MOCK_BASE_URL: http://localhost:9000/v1
```

Note:

```text
Do not run GPU vLLM in CI.
Use mock backend tests.
```

---

## 30. Testing Strategy

### 30.1 Unit Tests

```text
test_auth.py
- missing API key returns 401
- invalid API key returns 401
- valid API key passes

test_rate_limit.py
- under limit passes
- over limit returns 429

test_request_id.py
- generates request ID
- propagates X-Request-ID

test_models.py
- model aliases resolve correctly

test_error_mapping.py
- backend timeout maps to 504
- backend unavailable maps to 502
```

### 30.2 API Tests

```text
test_health.py
- /health returns ok
- /ready checks backend

test_chat_proxy.py
- non-streaming proxy works
- response shape is OpenAI-compatible

test_streaming.py
- streaming proxy yields SSE chunks
- TTFT is recorded

test_metrics.py
- /metrics returns Prometheus format
- request counter increments
```

### 30.3 Integration Tests

```text
1. Start mock backend.
2. Start gateway.
3. Call OpenAI SDK.
4. Call streaming endpoint.
5. Verify metrics.
6. Verify rate limit.
7. Run benchmark small mode.
```

---

## 31. README Structure

```markdown
# Mini LLM Serving Platform

A production-style OpenAI-compatible LLM serving gateway with FastAPI, vLLM, streaming, API key auth, Redis rate limiting, Prometheus/Grafana observability, benchmarking, Docker Compose, and RAG integration.

## Demo

Screenshots:
- OpenAI SDK call
- streaming response
- Grafana dashboard
- benchmark report

## Why This Project

This is not just `vllm serve`. It shows how to build a small internal LLM serving gateway.

## Architecture

Mermaid diagram.

## Features

- OpenAI-compatible `/v1/chat/completions`
- Streaming and non-streaming responses
- FastAPI gateway
- vLLM backend
- no-GPU mock backend
- API key authentication
- Redis rate limiting
- model aliases
- structured JSON logging
- Prometheus metrics
- Grafana dashboard
- direct backend vs gateway benchmark
- Docker Compose
- optional Kubernetes / Helm
- RAG Assistant integration

## Quickstart: No GPU

```bash
cp .env.example .env
docker compose up --build
uv run python benchmark/client_smoke_test.py
make benchmark
```

## Quickstart: With GPU

```bash
cp .env.example .env
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

## API Example

OpenAI SDK example.

## Benchmark Results

Table and link to docs/benchmark_report.md.

## Observability

Grafana screenshot and metrics explanation.

## Design Decisions

Link to docs/design_decisions.md.

## RAG Integration

Link to docs/rag_integration.md.

## Limitations

This is a production-style portfolio project, not a full enterprise inference platform.

Missing:
- autoscaling
- multi-tenant billing
- GPU scheduling
- distributed model parallel deployment
- LoRA adapter routing
- SLA/SLO
- incident response
- full Kubernetes production setup

## Future Work

- Ray Serve LLM deployment
- KEDA autoscaling
- LoRA adapter routing
- SGLang/TGI backend comparison
- TPM rate limiting
- canary routing
```

---

## 32. Required Docs

### 32.1 `docs/design_decisions.md`

Answer these:

```text
1. Why build a gateway instead of exposing vLLM directly?
2. Why OpenAI-compatible API?
3. Why no-GPU mock backend?
4. Why streaming?
5. Why API key auth?
6. Why Redis rate limiting?
7. Why Prometheus and Grafana?
8. What is the difference between gateway metrics and vLLM metrics?
9. Why benchmark p95 and TTFT instead of only average latency?
10. Why default to not logging raw prompts?
11. Why Docker Compose first?
12. Why Kubernetes/Helm only optional?
13. Why vLLM instead of SGLang/TGI for MVP?
14. How does this integrate with the RAG assistant?
```

### 32.2 `docs/failure_analysis.md`

Template:

```markdown
# Failure Analysis

## Backend Timeout

- Request:
- Backend:
- Observed behavior:
- Root cause:
- Fix:

## Streaming Broken

- Request:
- Expected SSE:
- Actual response:
- Root cause:
- Fix:

## Rate Limit False Positive

- API key:
- Limit:
- Observed count:
- Root cause:
- Fix:

## High P95 Latency

- Benchmark setup:
- P50:
- P95:
- TTFT:
- Output tok/s:
- Root cause:
- Fix:

## Gateway Overhead Too High

- Direct backend:
- Gateway routed:
- Difference:
- Root cause:
- Fix:
```

### 32.3 `docs/rag_integration.md`

Include:

```text
1. Architecture: RAG → gateway → vLLM/mock.
2. Environment variables.
3. Smoke test.
4. Why OpenAI-compatible APIs make this easy.
5. Limitations of local model quality.
```

---

## 33. Implementation Plan

### Week 1: Gateway + Mock

```text
Day 1:
- repo setup
- FastAPI skeleton
- /health /ready

Day 2:
- OpenAI-compatible schemas
- mock backend non-streaming

Day 3:
- mock backend streaming
- gateway non-streaming proxy

Day 4:
- gateway streaming proxy
- OpenAI SDK smoke test

Day 5:
- API key auth
- request ID middleware

Day 6:
- Redis RPM rate limiting

Day 7:
- structured logging
- tests
```

### Week 2: Metrics + Benchmark

```text
Day 8:
- Prometheus metrics

Day 9:
- /metrics endpoint
- metrics tests

Day 10:
- benchmark prompt datasets

Day 11:
- async benchmark runner

Day 12:
- TTFT / TPOT / ITL calculation

Day 13:
- benchmark report generator

Day 14:
- Docker Compose no-GPU stack
```

### Week 3: vLLM + Grafana

```text
Day 15:
- vLLM run script
- model alias mapping

Day 16:
- vLLM backend config

Day 17:
- docker-compose.gpu.yml

Day 18:
- Prometheus config

Day 19:
- Grafana dashboard

Day 20:
- direct vLLM vs gateway benchmark

Day 21:
- docs/benchmark_report.md
```

### Week 4: Polish + RAG Integration

```text
Day 22:
- RAG integration smoke test

Day 23:
- docs/rag_integration.md

Day 24:
- GitHub Actions

Day 25:
- optional Kubernetes manifests

Day 26:
- README screenshots

Day 27:
- docs/design_decisions.md
- docs/failure_analysis.md

Day 28:
- 2-minute demo recording
- CV bullet finalization
```

---

## 34. Final Acceptance Checklist

Before adding to CV:

```text
[ ] GitHub repo public or shareable.
[ ] README has architecture diagram.
[ ] No-GPU docker compose works.
[ ] Mock backend works.
[ ] OpenAI SDK smoke test passes.
[ ] Non-streaming proxy works.
[ ] Streaming proxy works.
[ ] API key auth works.
[ ] Redis rate limiting works.
[ ] /metrics works.
[ ] Prometheus scrapes gateway.
[ ] Grafana dashboard screenshot exists.
[ ] Benchmark report exists.
[ ] Direct backend vs gateway benchmark exists if GPU is available.
[ ] RAG integration smoke test exists.
[ ] CI passes.
[ ] docs/design_decisions.md exists.
[ ] docs/failure_analysis.md exists.
[ ] README limitations are honest.
[ ] CV bullets match implemented features.
```

---

## 35. CV Bullets

Use 2–3 bullets if CV is tight:

```text
OpenAI-Compatible LLM Serving Platform with vLLM
Python, FastAPI, vLLM, Redis, Prometheus, Grafana, Docker, GitHub Actions

- Built a FastAPI gateway in front of vLLM with OpenAI-compatible chat completions, streaming proxy, model aliases, API key auth, Redis rate limiting, request IDs, and structured logging.
- Added Prometheus/Grafana observability for request rate, error rate, p95 latency, TTFT, token throughput, backend timeouts, and rate-limited requests.
- Created async benchmarks comparing direct vLLM vs gateway-routed inference across concurrency levels, measuring RPS, TTFT, p95 latency, output tokens/sec, error rate, and gateway overhead.
```

If integrated with RAG:

```text
- Integrated the gateway as a drop-in OpenAI-compatible backend for a production-style RAG assistant, enabling local/self-hosted LLM inference without changing the RAG client interface.
```

---

## 36. Interview Opening Pitch

> This project is a production-style LLM serving gateway. Instead of directly exposing vLLM, I built a FastAPI gateway that provides an OpenAI-compatible API, streaming proxy, API key authentication, Redis rate limiting, request IDs, structured logging, Prometheus metrics, and Grafana dashboards. I also created a no-GPU mock backend so the project can be reproduced anywhere, and a vLLM backend for GPU environments. The benchmark suite compares direct vLLM calls with gateway-routed calls and measures TTFT, p95 latency, output tokens per second, RPS, and gateway overhead. The gateway can also be used as a drop-in backend for my RAG assistant through the OpenAI-compatible base URL.

---

## 37. High-Frequency Interview Questions

### Q1. Why not expose vLLM directly?

> Directly exposing vLLM is fine for experiments, but an internal platform usually needs authentication, rate limiting, logging, metrics, model aliases, error normalization, and stable client-facing APIs. The gateway adds these platform features.

### Q2. Why OpenAI-compatible API?

> It lets existing clients, LiteLLM, OpenAI SDK, and my RAG assistant switch between hosted APIs and self-hosted inference by changing only the base URL and API key.

### Q3. Why mock backend?

> It makes the gateway reproducible without GPU. I can test streaming, auth, rate limiting, metrics, and benchmark tooling locally or in CI.

### Q4. What is TTFT?

> Time to first token. It measures how quickly a streaming user sees the first output token and is often more important for perceived latency than total completion time.

### Q5. What is gateway overhead?

> The latency added by routing through the gateway instead of calling vLLM directly. It includes auth, rate limiting, logging, metrics, proxying, and serialization overhead.

### Q6. Why Prometheus and Grafana?

> Prometheus gives time-series service metrics and Grafana visualizes them. This is useful for request rate, error rate, latency, TTFT, token throughput, and rate limiting behavior.

### Q7. Why not log prompts?

> Prompts may contain sensitive user or business data. The default is to log metadata, not raw prompts. Raw prompt logging should only be enabled explicitly in a safe development environment.

### Q8. How would you scale this?

> I would add autoscaling, queue-aware routing, per-model replicas, distributed deployment, stronger rate limiting, model warmup, GPU scheduling, and potentially Ray Serve LLM or Kubernetes autoscaling based on Prometheus metrics.

### Q9. How does this connect to your RAG project?

> The RAG application calls an OpenAI-compatible API through LiteLLM or the OpenAI SDK. By setting OPENAI_BASE_URL to this gateway, the RAG app can use local vLLM instead of hosted APIs without changing application logic.

### Q10. What are the limitations?

> It is not a full enterprise inference platform. It lacks autoscaling, tenant billing, GPU scheduling, LoRA adapter routing, full incident response, and production SLA/SLO. It is production-style and designed for learning and portfolio demonstration.

---

## 38. Common Mistakes to Avoid

```text
1. Only running vLLM without a gateway.
2. No mock backend, making the project impossible to reproduce without GPU.
3. No streaming proxy.
4. No OpenAI SDK smoke test.
5. No benchmark report.
6. Only reporting average latency, not p95 or TTFT.
7. No Prometheus/Grafana dashboard.
8. Logging raw prompts or API keys.
9. Overclaiming enterprise production readiness.
10. Adding Kubernetes before core gateway features are stable.
```

---

## 39. Troubleshooting

### 39.1 Gateway Cannot Reach Backend

Check:

```text
[ ] BACKEND_TYPE is correct
[ ] MOCK_BASE_URL or VLLM_BASE_URL is correct
[ ] backend container is running
[ ] Docker service name is correct
[ ] /v1/models works on backend
```

### 39.2 Streaming Does Not Work

Check:

```text
[ ] client uses stream=true
[ ] gateway returns text/event-stream
[ ] backend returns SSE
[ ] proxy does not buffer full response
[ ] curl uses -N
```

### 39.3 Rate Limit Not Working

Check:

```text
[ ] Redis is running
[ ] RATE_LIMIT_ENABLED=true
[ ] API key hash is stable
[ ] TTL is set correctly
```

### 39.4 Metrics Missing

Check:

```text
[ ] /metrics endpoint works
[ ] Prometheus target is up
[ ] labels are not too high-cardinality
[ ] requests have actually been sent
```

### 39.5 High Gateway Overhead

Check:

```text
[ ] HTTP client connection reuse
[ ] logging overhead
[ ] streaming buffering
[ ] Redis latency
[ ] metrics label cardinality
[ ] backend timeout settings
```

---

## 40. References and Design Inspirations

Use these in README as references, not as “copied from” claims.

```text
- vLLM OpenAI-compatible server documentation
- vLLM production metrics documentation
- vLLM metrics design documentation
- SGLang OpenAI-compatible API documentation
- Hugging Face TGI documentation
- Prometheus client library documentation
- OpenAI Python SDK usage pattern
```

---

## 41. Final Implementation Principle

Build the smallest serving platform that proves real engineering competence:

```text
OpenAI-compatible API
streaming
auth
rate limiting
metrics
benchmark
Docker
RAG integration
honest limitations
```

Do not claim:

```text
full enterprise inference platform
production SLA
autoscaling-ready GPU platform
```

Claim:

```text
production-style LLM serving gateway with reproducible no-GPU demo, optional vLLM backend, benchmark reports, observability, and RAG integration.
```
