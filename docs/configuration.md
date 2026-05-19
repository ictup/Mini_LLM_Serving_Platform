# Configuration Guide

This project keeps runtime configuration explicit so the same Gateway can run
against a mock backend locally or a real vLLM backend in Docker, Kubernetes, and
Helm deployments.

## Configuration Sources

| Environment | Primary source | Purpose |
| --- | --- | --- |
| Local processes | `.env` copied from `.env.example` | Developer defaults for `uvicorn` and benchmark scripts |
| Docker no-GPU | `docker-compose.yml` | Gateway, mock backend, Redis, Prometheus, and Grafana |
| Docker GPU | `docker-compose.gpu.yml` plus shell environment | Overrides Gateway to use vLLM and starts the vLLM container |
| Kubernetes no-GPU | `deploy/k8s/gateway-config.yaml` and `deploy/k8s/gateway-secret.yaml` | Static manifests for the mock stack |
| Kubernetes GPU | `deploy/k8s-gpu/*` patches and vLLM manifests | Adds vLLM and rewires Gateway to the vLLM service |
| Helm | `deploy/helm/values.yaml` | Parameterized Kubernetes deployment for mock or vLLM mode |
| Production hardening | `docs/production_hardening.md` | Ingress/TLS, external Secrets, HPA, warmup, and Grafana persistence |
| Gateway defaults | `gateway/app/core/config.py` | Last-resort defaults when no environment value is supplied |

## Gateway Runtime Variables

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `APP_NAME` | No | `mini-llm-serving-platform` | Service name used in logs and metrics labels. |
| `ENV` | No | `local` | Environment label such as `local`, `docker`, or `k8s`. |
| `LOG_LEVEL` | No | `INFO` | Gateway log level. |
| `API_KEYS` | Yes | `dev-key,team-a-key` | Comma-separated client Bearer tokens accepted by the Gateway. |
| `RATE_LIMIT_ENABLED` | No | `false` in code, enabled in deploy files | Enables Redis-backed per-key RPM, TPM, and concurrent request limiting. |
| `RATE_LIMIT_RPM` | No | `60` | Requests per minute allowed for each API key. |
| `RATE_LIMIT_TPM` | No | `60000` | Estimated tokens per minute allowed for each API key. |
| `RATE_LIMIT_CONCURRENT_REQUESTS` | No | `20` | Simultaneous in-flight chat requests allowed for each API key. |
| `RATE_LIMIT_DEFAULT_COMPLETION_TOKENS` | No | `256` | Output-token budget reserved when a request omits `max_tokens`. |
| `REDIS_URL` | When rate limiting is enabled | `redis://localhost:6379/0` | Redis connection URL used by the rate limiter. |
| `MAX_REQUEST_BODY_BYTES` | No | `1048576` | Maximum accepted HTTP request body size. Oversized requests return `413`. |
| `MAX_CHAT_MESSAGES` | No | `64` | Maximum number of messages in one chat completion request. |
| `MAX_CHAT_MESSAGE_CHARS` | No | `16000` | Maximum character count for a single chat message content field. |
| `MAX_CHAT_TOTAL_MESSAGE_CHARS` | No | `64000` | Maximum combined character count across all chat message content fields. |
| `BACKEND_TYPE` | No | `mock` | Selects `mock` or `vllm` backend routing. |
| `MOCK_BASE_URL` | In mock mode | `http://localhost:9000/v1` | OpenAI-compatible mock backend base URL. |
| `VLLM_BASE_URL` | In vLLM mode | `http://localhost:8000/v1` | OpenAI-compatible vLLM backend base URL. |
| `VLLM_API_KEY` | In vLLM mode | empty in code, `local-vllm-key` in examples | Bearer token used from Gateway to vLLM. |
| `BACKEND_TIMEOUT_SECONDS` | No | `120` | Timeout for non-streaming upstream calls. |
| `STREAMING_TIMEOUT_SECONDS` | No | `300` | Timeout budget for streaming upstream calls. |
| `DEFAULT_MODEL` | No | `mock` | Model used when a client request omits `model`. |
| `MODEL_ALIASES_JSON` | No | `{"mock":"mock"}` | JSON object mapping client-facing aliases to backend model ids. |
| `METRICS_ENABLED` | No | `true` | Enables Prometheus metrics output. |

## vLLM Runtime Variables

These values configure the vLLM server itself. They are consumed by
`docker-compose.gpu.yml`, `deploy/k8s-gpu`, and the Helm `vllm` values.

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `VLLM_MODEL` | Yes | `Qwen/Qwen2.5-0.5B-Instruct` | Hugging Face model id served by vLLM. The default is validated on an 8GB RTX 4060 Laptop GPU. |
| `VLLM_IMAGE_TAG` | No | `v0.8.5.post1` | Docker tag for `vllm/vllm-openai` in Compose GPU mode. |
| `VLLM_DTYPE` | No | `float16` | vLLM dtype argument. |
| `VLLM_MAX_MODEL_LEN` | No | `4096` | Maximum model context length. |
| `VLLM_GPU_MEMORY_UTILIZATION` | No | `0.75` | Fraction of GPU memory vLLM can target. |
| `VLLM_SWAP_SPACE` | No | `1` | vLLM CPU swap space in GiB. |
| `VLLM_USE_V1` | No | `0` | vLLM engine switch. `0` uses the v0 engine for local Docker compatibility. |
| `VLLM_API_KEY` | Yes | `local-vllm-key` | API key enforced by vLLM and used by the Gateway. |
| `HUGGING_FACE_HUB_TOKEN` | For gated models | empty | Token required to download gated Hugging Face models. |

## Model Alias Design

Clients should call stable aliases such as `mock` or `qwen-small`. The Gateway
translates those aliases to backend model ids through `MODEL_ALIASES_JSON`.

Example for local mock mode:

```env
BACKEND_TYPE=mock
DEFAULT_MODEL=mock
MODEL_ALIASES_JSON={"mock":"mock","qwen-small":"mock"}
```

Example for vLLM mode:

```env
BACKEND_TYPE=vllm
VLLM_MODEL=Qwen/Qwen2.5-0.5B-Instruct
DEFAULT_MODEL=qwen-small
MODEL_ALIASES_JSON={"qwen-small":"Qwen/Qwen2.5-0.5B-Instruct"}
```

This keeps client code stable while allowing the served backend model to change.

## Secret Handling

Local development may use `.env` values directly. Do not commit a real `.env`
file. The repository only includes `.env.example`.

For Kubernetes, keep sensitive values in Secrets:

- `API_KEYS`: client-to-Gateway keys.
- `VLLM_API_KEY`: Gateway-to-vLLM key and vLLM server key.
- `HUGGING_FACE_HUB_TOKEN`: only needed for gated model downloads.

For Helm, replace the example values before deploying outside local
experiments:

```bash
helm upgrade --install mini-llm deploy/helm \
  --namespace mini-llm-serving \
  --create-namespace \
  --set gateway.apiKeys='<client-keys>' \
  --set vllm.enabled=true \
  --set mockBackend.enabled=false \
  --set vllm.apiKey='<gateway-to-vllm-key>' \
  --set vllm.huggingFaceHubToken='<hf-token-if-needed>'
```

For shared environments, prefer pre-created Secrets or External Secrets:

```bash
helm upgrade --install mini-llm deploy/helm \
  --namespace mini-llm-serving \
  --set gateway.existingSecretName=gateway-secret \
  --set vllm.existingSecretName=vllm-secret
```

## Backend Mode Checklist

Mock mode:

- `BACKEND_TYPE=mock`
- `MOCK_BASE_URL` points to the mock backend service.
- `DEFAULT_MODEL` and `MODEL_ALIASES_JSON` resolve to `mock`.

vLLM mode:

- `BACKEND_TYPE=vllm`
- `VLLM_BASE_URL` points to the vLLM OpenAI-compatible endpoint.
- `VLLM_API_KEY` matches the vLLM server `--api-key`.
- `DEFAULT_MODEL` is a client-facing alias.
- `MODEL_ALIASES_JSON` maps that alias to the real `VLLM_MODEL`.
- `HUGGING_FACE_HUB_TOKEN` is set if the model is gated.
