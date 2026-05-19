# GitOps Deployment Examples

This directory contains Argo CD `Application` examples that continuously sync
the Helm chart from this repository.

## Files

| File | Purpose |
| --- | --- |
| `argocd-application-mock.yaml` | No-GPU mock backend stack for cluster validation. |
| `argocd-application-vllm.yaml` | CUDA-backed vLLM stack for GPU nodes. |

## Prerequisites

- Argo CD is installed in the `argocd` namespace.
- The Gateway image is published to
  `ghcr.io/ictup/mini-llm-serving-platform:main`, or the image value is changed
  to your registry.
- `gateway-secret` exists in `mini-llm-serving` and contains `API_KEYS`.
- For vLLM mode, `gateway-secret` also contains `VLLM_API_KEY`, and
  `vllm-secret` contains `VLLM_API_KEY` plus optional
  `HUGGING_FACE_HUB_TOKEN`.
- The vLLM application requires a Kubernetes node with an NVIDIA GPU device
  plugin and enough VRAM for the configured model.

## Apply

```bash
kubectl apply -f deploy/gitops/argocd-application-mock.yaml
```

For the GPU path:

```bash
kubectl apply -f deploy/gitops/argocd-application-vllm.yaml
```

Inspect sync state:

```bash
argocd app get mini-llm-serving-mock
argocd app get mini-llm-serving-vllm
```

These examples intentionally reference existing Secrets instead of embedding
local placeholder keys in GitOps manifests.
