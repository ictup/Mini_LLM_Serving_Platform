# RAG Integration

This project can act as a drop-in OpenAI-compatible LLM backend for a RAG
application. The RAG app keeps its retrieval and context-building logic, then
sends the final chat request to the Gateway instead of a hosted API.

## Architecture

```text
User question
  -> RAG retriever
  -> context builder
  -> OpenAI-compatible client
  -> Mini LLM Gateway
  -> mock backend locally or vLLM with GPU
```

The Gateway does not perform retrieval. Its role is to provide the LLM serving
contract used after retrieval has produced context.

## Environment Variables

Most OpenAI-compatible RAG clients can be pointed at the Gateway with these
values:

```env
OPENAI_BASE_URL=http://localhost:8080/v1
OPENAI_API_KEY=dev-key
LLM_MODEL=mock
```

For vLLM mode, use the client-facing alias configured in `MODEL_ALIASES_JSON`:

```env
OPENAI_BASE_URL=http://localhost:8080/v1
OPENAI_API_KEY=dev-key
LLM_MODEL=qwen-small
```

`OPENAI_API_KEY` is the client-to-Gateway key from `API_KEYS`. It is not the
same as `VLLM_API_KEY`, which is used only between the Gateway and vLLM.

## Minimal RAG Smoke Test

Run the RAG smoke test against an already running Gateway:

```bash
uv run python benchmark/rag_integration_smoke_test.py
```

Run a full local mock stack and then execute the RAG smoke test:

```bash
uv run python scripts/local_e2e.py --smoke-script benchmark/rag_integration_smoke_test.py
```

Or through Make:

```bash
make local-e2e-rag
```

The smoke test builds a RAG-style chat request:

- system message: instructs the model to answer from context.
- user message: includes numbered context passages and a question.
- model: uses the client-facing alias, default `mock`.

The mock backend echoes the request, so this smoke test validates API
compatibility and routing. It does not validate retrieval quality or real model
grounding.

## Custom Context Example

```bash
uv run python benchmark/rag_integration_smoke_test.py \
  --question "What does the Gateway add in front of vLLM?" \
  --context "The Gateway adds API key authentication and request IDs." \
  --context "The Gateway records Prometheus metrics and supports model aliases."
```

## Python Client Pattern

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8080/v1",
    api_key="dev-key",
)

contexts = [
    "The Gateway exposes an OpenAI-compatible API.",
    "The Gateway can route to a mock backend or vLLM.",
]

messages = [
    {
        "role": "system",
        "content": "Answer using only the provided context.",
    },
    {
        "role": "user",
        "content": (
            "Context:\n"
            f"[1] {contexts[0]}\n"
            f"[2] {contexts[1]}\n\n"
            "Question: How does a RAG app call the platform?\n\n"
            "Answer:"
        ),
    },
]

response = client.chat.completions.create(
    model="mock",
    messages=messages,
)

print(response.choices[0].message.content)
```

## Integration Checklist

- Confirm the RAG app uses the OpenAI SDK, LiteLLM, LangChain, LlamaIndex, or
  another OpenAI-compatible client.
- Set the client base URL to the Gateway `/v1` endpoint.
- Use a Gateway API key from `API_KEYS`.
- Use a client-facing model alias returned by `/v1/models`.
- Keep retrieval, reranking, and context formatting inside the RAG app.
- Use Gateway logs and `X-Request-ID` to trace generation calls.
- Use Gateway metrics to observe latency, error rate, and streaming TTFT.

## What Is Still Not Implemented

This repository now includes a project-local RAG smoke test. It does not yet
include an adapter for a specific external RAG application. To wire in an
existing RAG project, point its OpenAI-compatible client configuration to this
Gateway and run the same questions through both hosted and Gateway-backed
models.
