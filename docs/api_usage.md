# API Usage Guide

The Gateway exposes an OpenAI-compatible API under `/v1`. Clients can use
plain HTTP, curl, or the official OpenAI Python SDK by pointing the SDK
`base_url` at the Gateway.

## Base URLs

| Mode | Gateway base URL | Notes |
| --- | --- | --- |
| Local process | `http://localhost:8080/v1` | Start Gateway with `make dev` or `uv run uvicorn ...`. |
| Docker Compose | `http://localhost:8080/v1` | Start with `docker compose up --build`. |
| Kubernetes port-forward | `http://localhost:8080/v1` | Run `kubectl -n mini-llm-serving port-forward svc/gateway 8080:8080`. |

## Authentication

`GET /v1/models` and `POST /v1/chat/completions` require a Bearer token:

```http
Authorization: Bearer dev-key
```

The accepted tokens come from `API_KEYS`. Local examples use `dev-key`.

Invalid or missing credentials return:

```json
{
  "error": {
    "message": "invalid api key",
    "type": "authentication_error",
    "code": "invalid_api_key",
    "param": null
  },
  "request_id": "req_..."
}
```

Every response includes an `X-Request-ID` header. Clients may provide their own
valid `X-Request-ID`; otherwise the Gateway generates one.

## Health and Readiness

Health checks the Gateway process only:

```bash
curl http://localhost:8080/health
```

Example response:

```json
{"status":"ok"}
```

Readiness checks the configured backend by calling its model list endpoint:

```bash
curl http://localhost:8080/ready
```

Example response:

```json
{
  "status": "ready",
  "backend": "ok",
  "backend_type": "mock",
  "models": "1"
}
```

## List Models

The Gateway returns client-facing model aliases, not necessarily the raw backend
model ids.

```bash
curl http://localhost:8080/v1/models \
  -H "Authorization: Bearer dev-key"
```

Example response:

```json
{
  "object": "list",
  "data": [
    {
      "id": "mock",
      "object": "model",
      "owned_by": "gateway"
    }
  ]
}
```

## Chat Completion

Non-streaming request:

```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer dev-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mock",
    "messages": [
      {"role": "user", "content": "Say hello from the Gateway."}
    ],
    "temperature": 0.2,
    "max_tokens": 64
  }'
```

Example mock response:

```json
{
  "id": "chatcmpl-mock-...",
  "object": "chat.completion",
  "created": 1760000000,
  "model": "mock",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Mock response to: Say hello from the Gateway."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 5,
    "completion_tokens": 8,
    "total_tokens": 13
  }
}
```

Supported request fields:

| Field | Required | Notes |
| --- | --- | --- |
| `model` | Yes | Client-facing alias such as `mock` or `qwen-small`. |
| `messages` | Yes | Non-empty list of chat messages. |
| `temperature` | No | Must be greater than or equal to `0` when supplied. |
| `top_p` | No | Must be between `0` and `1` when supplied. |
| `max_tokens` | No | Must be greater than `0` when supplied. |
| `stream` | No | Defaults to `false`. |
| `stop` | No | String or list of strings. |
| `user` | No | Optional end-user identifier passed through to the backend. |

Allowed message roles are `system`, `user`, `assistant`, and `tool`.

## Streaming Chat Completion

Set `stream` to `true` to receive Server-Sent Events:

```bash
curl -N http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer dev-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mock",
    "messages": [
      {"role": "user", "content": "Stream a short answer."}
    ],
    "stream": true
  }'
```

The response is an SSE stream:

```text
data: {"id":"chatcmpl-mock-...","object":"chat.completion.chunk",...}

data: {"id":"chatcmpl-mock-...","object":"chat.completion.chunk",...}

data: [DONE]
```

The Gateway rewrites streamed `model` values back to the client-facing alias, so
clients see the same model name they requested.

## Python SDK

Install project dependencies, then use the OpenAI SDK against the Gateway:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="dev-key",
)

response = client.chat.completions.create(
    model="mock",
    messages=[{"role": "user", "content": "Say hello."}],
)

print(response.choices[0].message.content)
```

Streaming with the SDK:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="dev-key",
)

chunks = client.chat.completions.create(
    model="mock",
    messages=[{"role": "user", "content": "Stream a short answer."}],
    stream=True,
)

for chunk in chunks:
    delta = chunk.choices[0].delta.content
    if delta:
        print(delta, end="", flush=True)
```

The repository also includes a smoke test:

```bash
uv run python benchmark/client_smoke_test.py
```

For vLLM mode, pass the alias configured in `MODEL_ALIASES_JSON`:

```bash
OPENAI_BASE_URL=http://localhost:8080/v1 \
OPENAI_API_KEY=dev-key \
LLM_MODEL=qwen-small \
uv run python benchmark/client_smoke_test.py
```

## Error Responses

Unknown model aliases return `400`:

```json
{
  "error": {
    "message": "model not found: missing-model",
    "type": "invalid_request_error",
    "code": "model_not_found",
    "param": null
  },
  "request_id": "req_..."
}
```

Backend failures are normalized into the same OpenAI-style error envelope with
the backend-derived status code and error code.

## Metrics

Prometheus metrics are available at:

```bash
curl http://localhost:8080/metrics
```

When `METRICS_ENABLED=false`, this endpoint returns `404`.
