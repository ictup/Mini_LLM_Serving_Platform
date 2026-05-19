# Design Decisions

This document explains the main engineering choices behind the mini LLM
serving platform. The goal is to make the project understandable as a
production-style serving gateway, not just a collection of scripts.

## Why Build a Gateway Instead of Exposing vLLM Directly?

vLLM already exposes an OpenAI-compatible API, so a direct client-to-vLLM setup
is enough for experiments. A platform Gateway adds the responsibilities that
usually sit around an inference engine:

- API key authentication.
- Request IDs for tracing.
- Rate limiting.
- Request and input size limits.
- Stable model aliases.
- Weighted model routes for canary and fallback targets.
- Error normalization.
- User-facing metrics.
- Rejection reason metrics.
- Structured logs.
- A single client-facing contract even if the backend changes.

The Gateway is deliberately thin. It does not own model execution. It owns
cross-cutting platform behavior.

## Why an OpenAI-Compatible API?

The OpenAI API shape is widely supported by SDKs, CLIs, benchmark tools, and
RAG frameworks. Supporting `/v1/models` and `/v1/chat/completions` means a
client can switch from a hosted provider to this Gateway by changing the
`base_url`, API key, and model name.

That choice also keeps the mock backend and vLLM backend interchangeable,
because both speak the same basic protocol.

## Why Keep a No-GPU Mock Backend?

The mock backend makes the platform reproducible on a laptop and in CI. It lets
the project test the Gateway's core behavior without a model download or CUDA
runtime:

- Non-streaming proxy behavior.
- Streaming SSE behavior.
- Authentication and error envelopes.
- Request ID propagation.
- Metrics emission.
- Benchmark tooling shape.
- Docker, Kubernetes, and Helm wiring.

The mock backend is not meant to simulate real model quality or GPU scheduling.
It is a reliable platform test double.

## Why Support Streaming?

LLM serving is not only about total completion latency. For chat UX, time to
first token is often the most visible latency. Streaming also changes proxy
implementation details: the Gateway must forward chunks without buffering the
entire response, preserve SSE framing, and report streaming-specific metrics.

The project supports both non-streaming and streaming calls so it can exercise
the two most common OpenAI-compatible usage patterns.

## Why API Key Authentication?

Even a small internal Gateway needs a boundary between clients and backend
inference. API keys provide a simple, testable first layer:

- Clients authenticate with `Authorization: Bearer <key>`.
- The Gateway can reject unauthenticated traffic before reaching the backend.
- Rate limiting can be keyed by API key.

This is intentionally simpler than OAuth or mTLS. Those are production options,
but they would distract from the serving-platform mechanics in this project.

## Why Redis-Backed Rate Limiting?

Rate limiting must work across more than one Gateway process. In-memory counters
would pass local tests but break when multiple replicas are deployed. Redis
provides a shared counter store that works locally, in Docker Compose, and in
Kubernetes.

The current implementation enforces request-per-minute, model-aware
token-per-minute, and concurrent in-flight request limits. Concurrent limits are
released when non-streaming calls finish or when streaming responses finish
iterating.

## Why Add Request and Input Size Limits?

LLM requests can become expensive before they reach the model. A very large
HTTP body consumes Gateway parsing memory, and an extremely large `messages`
array can waste validation, logging, rate-limit, and backend capacity.

The Gateway therefore applies two layers:

- A request body byte limit at middleware level, before request parsing.
- Chat-specific message count and character limits after schema validation but
  before rate limiting and backend calls.

The second layer uses character counts so it stays backend-neutral. The
token-per-minute limiter is separate and can use model-aware tokenizer profiles
or exact local tokenizer files for capacity accounting.

## Why Prometheus and Grafana?

Prometheus and Grafana are common infrastructure choices for service metrics.
They are also easy to run locally through Docker Compose.

The Gateway metrics answer client-facing questions:

- How many requests are arriving?
- What is the error rate?
- What is p95 latency?
- What is streaming TTFT?
- Which model aliases are used?
- Is the Gateway rate limiting traffic?

Grafana turns those metrics into an operational dashboard that can be checked
while running smoke tests or benchmarks.

Prometheus alert rules are kept beside the scrape configuration so local Docker,
static Kubernetes, and Helm deployments share the same operational signals. The
rules focus on symptoms that matter for LLM serving: Gateway error ratio,
request latency, streaming TTFT, rejection rate, vLLM waiting requests, KV cache
pressure, and vLLM TTFT.

Error responses also emit `gateway_http_rejections_total` with a bounded
`reason` label derived from Gateway error codes. This is more actionable than
only looking at status codes while still avoiding high-cardinality labels.

## Gateway Metrics vs vLLM Metrics

Gateway metrics and vLLM metrics answer different questions.

Gateway metrics describe the user-facing API path:

- Authentication failures.
- Rate-limit decisions.
- Gateway request latency.
- Backend error mapping.
- Streaming TTFT as observed by clients.
- Requests grouped by client-facing model alias.

vLLM metrics describe the inference engine:

- Scheduler queueing.
- KV cache pressure.
- Token throughput.
- Engine-side TTFT and end-to-end latency.
- Running and waiting request counts.

When latency is high, Gateway metrics show whether the platform layer is adding
overhead. vLLM metrics show whether the inference engine is saturated.

## Why Benchmark p95 and TTFT Instead of Only Average Latency?

Average latency hides user-visible tail behavior. p95 shows what slower users
experience under concurrency. TTFT measures how quickly a streaming client sees
the first token, which is often more important than total completion time for
interactive applications.

The benchmark runner records both whole-request metrics and streaming metrics
so direct-backend and Gateway-routed calls can be compared.

## Why Avoid Logging Raw Prompts by Default?

Prompts may contain user data, business data, credentials, or proprietary
context. The Gateway logs request metadata such as request ID, model alias,
backend type, stream flag, and status, but it does not log raw prompt text.

Prompt logging should be an explicit development-only choice, not the default
behavior of a serving Gateway.

## Why Docker Compose First?

Docker Compose gives a reproducible local stack without requiring a Kubernetes
cluster. It is the fastest way to prove service boundaries:

- Gateway.
- Mock backend.
- Redis.
- Prometheus.
- Grafana.
- Optional vLLM service when GPU is available.

Once those boundaries are stable, Kubernetes and Helm can mirror them.

## Why Keep Kubernetes and Helm Minimal?

The Kubernetes and Helm assets are deployment skeletons with practical
production hooks. They prove that the service boundaries can be expressed as
manifests and parameterized through Helm, while leaving cluster-specific choices
to the target environment.

The current chart includes optional ingress, HPA, external Secret references,
and vLLM startup probes. It still does not include ServiceMonitor CRDs,
organization-specific external secret stores, GPU node autoscaling, persistent
cluster storage, or multi-model routing. Those choices depend on the target
cluster and organization.

## Why vLLM Instead of SGLang or TGI for the MVP?

vLLM is a practical primary backend for this project because it is widely used,
OpenAI-compatible, focused on high-throughput serving, and exposes metrics that
fit the observability story.

Other engines remain relevant:

| Engine | Why relevant | Why not primary here |
| --- | --- | --- |
| vLLM | Mature OpenAI-compatible serving with strong throughput and metrics | Primary backend |
| SGLang | Strong for structured and agentic workloads | Future comparison |
| TGI | Production inference server with streaming and metrics | Reference backend |
| TensorRT-LLM | High performance on NVIDIA stacks | Too hardware-specific for this MVP |

Implementing every backend would dilute the project. The Gateway design keeps
the backend boundary explicit so another backend can be added later.

## How This Connects to a RAG Assistant

A RAG application that already uses the OpenAI SDK or an OpenAI-compatible
client can point to this Gateway by changing:

- `OPENAI_BASE_URL`.
- `OPENAI_API_KEY`.
- The model alias.

The repository includes a project-local RAG smoke test that validates this
client boundary. The intended path is:

```text
RAG application -> OpenAI-compatible Gateway -> mock or vLLM backend
```

That keeps the RAG application independent from whether inference is hosted,
mocked, or served through local vLLM.
