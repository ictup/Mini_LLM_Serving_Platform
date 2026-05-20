# Production Hardening Guide

This guide covers the production-oriented extensions included with the project.
They are still intentionally lightweight, but each item is represented as code,
configuration, or an executable workflow instead of only a note.

## Error Reason Metrics

The Gateway exposes stable rejection reasons through:

```promql
gateway_http_rejections_total{reason="invalid_api_key"}
gateway_http_rejections_total{reason="rate_limit_exceeded"}
gateway_http_rejections_total{reason="token_rate_limit_exceeded"}
gateway_http_rejections_total{reason="concurrent_request_limit_exceeded"}
gateway_http_rejections_total{reason="request_body_too_large"}
gateway_http_rejections_total{reason="chat_message_too_large"}
gateway_http_rejections_total{reason="model_not_found"}
gateway_http_rejections_total{reason="backend_timeout"}
```

The metric uses the `X-Gateway-Error-Code` response header produced by Gateway
error handlers. This keeps Prometheus label cardinality bounded while making
Grafana panels useful for triage.

## Ingress and TLS

The static Kubernetes stack includes `deploy/k8s/gateway-ingress.yaml` with an
NGINX-style HTTPS ingress example for `mini-llm.local`.

Before using it outside a local cluster:

- Replace `mini-llm.local` with the real hostname.
- Create the `mini-llm-serving-tls` TLS Secret through cert-manager, your cloud
  load balancer, or your platform secret process.
- Keep the ingress proxy body size aligned with `MAX_REQUEST_BODY_BYTES`.

The Helm chart keeps ingress disabled by default. Enable it with values:

```bash
helm upgrade --install mini-llm deploy/helm \
  --namespace mini-llm-serving \
  --create-namespace \
  --set gateway.ingress.enabled=true \
  --set gateway.ingress.host=llm.example.com \
  --set gateway.ingress.tlsSecretName=llm-example-com-tls
```

## Secret Management

Example manifests use obvious placeholder values such as
`replace-me-client-key` and `replace-me-vllm-key`. For shared environments,
create Secrets outside the release and tell Helm to reference them:

```bash
kubectl -n mini-llm-serving create secret generic gateway-secret \
  --from-literal=API_KEYS='<client-keys>' \
  --from-literal=VLLM_API_KEY='<gateway-to-vllm-key>'

kubectl -n mini-llm-serving create secret generic vllm-secret \
  --from-literal=VLLM_API_KEY='<gateway-to-vllm-key>' \
  --from-literal=HUGGING_FACE_HUB_TOKEN='<hf-token-if-needed>'

helm upgrade --install mini-llm deploy/helm \
  --namespace mini-llm-serving \
  --set gateway.existingSecretName=gateway-secret \
  --set vllm.existingSecretName=vllm-secret
```

If the cluster uses External Secrets Operator, start from
`deploy/k8s/examples/external-secrets.yaml` and replace the SecretStore and
remote keys with your provider-specific names.

Never commit real OpenAI, Hugging Face, vLLM, or Gateway API keys. If a key is
accidentally committed or pasted into a repository, revoke it and rotate the
consumer configuration before continuing.

## Autoscaling

The static Kubernetes stack includes a Gateway HPA:

```bash
kubectl -n mini-llm-serving get hpa gateway
```

It scales the stateless Gateway deployment from 1 to 3 replicas on CPU
utilization. This requires metrics-server and CPU requests on the Gateway pod.

The Helm chart keeps autoscaling disabled by default. Enable it with:

```bash
helm upgrade --install mini-llm deploy/helm \
  --namespace mini-llm-serving \
  --set gateway.autoscaling.enabled=true \
  --set gateway.autoscaling.maxReplicas=5
```

For real GPU serving, do not rely only on Gateway CPU. Compare Gateway latency,
Gateway rejection reasons, vLLM waiting requests, and vLLM KV cache pressure.
GPU autoscaling should be cluster-specific and capacity-aware.

## vLLM Startup, Readiness, and Warmup

vLLM can take several minutes to download and load a model. The GPU manifests
and Helm chart now use a `startupProbe` so Kubernetes does not restart vLLM
while the model is still loading. Docker GPU mode also waits for the vLLM
healthcheck before starting Gateway traffic.

After the Gateway is ready, run a small warmup request:

```bash
uv run python scripts/warmup_gateway.py \
  --base-url http://localhost:8080/v1 \
  --api-key dev-key \
  --model qwen-small
```

For large models, run warmup before benchmark collection so the first measured
request does not include cold-start effects.

## Grafana Persistence and Dashboard Workflow

Docker Compose now persists Grafana state with the `grafana-data` named volume.
Provisioned dashboards still live as JSON files under
`monitoring/grafana/dashboards`, so dashboard changes can be reviewed in Git.

Operational workflow:

- Treat dashboard JSON in this repository as the source of truth.
- Export useful UI edits from Grafana back into `monitoring/grafana/dashboards`.
- Back up or snapshot the `grafana-data` volume only when local UI state matters.
- Prefer adding panels with bounded labels such as `path`, `status_code`,
  `reason`, `model`, and `backend_model`.

## GPU Telemetry

The GPU Docker Compose override starts NVIDIA DCGM exporter and Prometheus
scrapes it at `dcgm-exporter:9400`. The `GPU Overview` dashboard shows GPU
utilization, framebuffer memory usage/free memory, and vLLM serving pressure in
one place.

For Kubernetes or Helm, enable the DCGM exporter only on GPU node pools. Shared
clusters commonly install DCGM exporter through the NVIDIA GPU Operator or the
official DCGM exporter Helm chart; this repository includes a lightweight
example for portfolio validation.

## Prometheus Alert Rules

The local and Kubernetes Prometheus configurations load
`/etc/prometheus/alerts.yml`. The source rule file for Docker Compose is
`monitoring/prometheus/alerts.yml`; the static Kubernetes and Helm paths render
the same alert groups into the `prometheus-config` ConfigMap.

Included alerts cover:

- `GatewayHighErrorRate`: Gateway error ratio above 5% for 5 minutes.
- `GatewayHighP95Latency`: Gateway p95 request latency above 2 seconds.
- `GatewayHighP95TTFT`: streaming TTFT above 750 ms.
- `GatewayHighRejectionRate`: sustained auth/rate-limit/request validation
  rejections.
- `VLLMWaitingRequests`: vLLM has queued requests for 5 minutes.
- `VLLMHighKVCacheUsage`: vLLM KV cache pressure above 85%.
- `VLLMHighP95TTFT`: vLLM engine TTFT above 1 second.

These rules are warning-level defaults for local and portfolio validation. In a
shared environment, connect Prometheus to Alertmanager or your managed
notification path, then tune thresholds against measured traffic and GPU
capacity.

## GitOps Deployment

Argo CD examples live under `deploy/gitops`. They sync the Helm chart from this
repository and override image, secret, mock, and vLLM values through
`valuesObject`.

The examples assume the Gateway image is published to GHCR by
`.github/workflows/container.yml` and that runtime Secrets already exist in the
target namespace. This keeps GitOps manifests free of real API keys.

Start with the mock Application to validate Argo CD sync without a GPU, then use
the vLLM Application for a GPU node pool:

```bash
kubectl apply -f deploy/gitops/argocd-application-mock.yaml
kubectl apply -f deploy/gitops/argocd-application-vllm.yaml
```

See `docs/gitops_deployment.md` for the full workflow and production notes.

## Terraform IaC Skeleton

`deploy/terraform` provides a small root module for teams that want the GitOps
entry point managed by Terraform. It creates the serving namespace, can create
placeholder Secrets for disposable labs, and manages an Argo CD `Application`
that syncs `deploy/helm`.

The module deliberately starts after cluster creation. It assumes a kubeconfig
and an existing Argo CD installation, because EKS, AKS, GKE, and local clusters
need different bootstrap code.

For shared environments, leave `create_placeholder_secrets=false` and create
`gateway-secret` / `vllm-secret` through External Secrets, Vault, or a managed
secret provider. If placeholder Secrets are enabled, those values are written to
Terraform state and must be treated as sensitive.

## Supply-Chain Security

The repository includes a dedicated security workflow at
`.github/workflows/security.yml`. It runs `pip-audit`, Trivy repository/IaC
scans, Trivy container-image scans, SARIF artifact uploads, and a CycloneDX
SBOM artifact for the built Gateway image.

The container publishing workflow also asks Docker Buildx to publish provenance
and SBOM attestations with the GHCR image. Dependabot is configured for GitHub
Actions, Python dependencies, and Docker base images.

The Trivy jobs are report-first by default so a newly disclosed base-image CVE
does not block every unrelated pull request. A production team can convert those
steps into hard gates once severity thresholds and remediation SLAs are agreed.
SARIF files are uploaded as workflow artifacts so the workflow remains usable in
personal repositories, forks, and organizations without GitHub code scanning
enabled.

See `docs/security.md` for local commands and production notes.

## Release Engineering

Release tags use `vMAJOR.MINOR.PATCH` and must match the `version` field in
`pyproject.toml`. The release workflow validates that contract before creating a
GitHub Release. The container image workflow publishes matching GHCR tags and
Buildx SBOM/provenance attestations.

Before cutting a release, update `CHANGELOG.md`, run the quality gate, validate
the intended tag with `scripts/check_release_version.py`, and push the tag.
Production GitOps values should use immutable release tags or image digests
rather than the moving `main` tag.

See `docs/release_process.md` for the full checklist.

## Final Production Checklist

- Replace all placeholder API keys and tokens.
- Configure ingress hostname and TLS Secret.
- Confirm metrics-server exists before relying on HPA.
- Validate vLLM startup on the target GPU hardware.
- Run Gateway warmup before benchmark collection.
- Check Grafana panels for request rate, latency, streaming behavior, and
  rejection reasons.
- Confirm Prometheus alert rules are loaded and route notifications through the
  environment's Alertmanager or managed alerting service.
- Validate the Argo CD Application sync path if the cluster is GitOps-managed.
- Validate the Terraform plan if cluster entry points are managed through IaC.
- Review security workflow findings and SBOM artifacts before tagging a release.
- Confirm release tag, changelog, GitHub Release, and GHCR image tag agree.
- Generate a direct-vs-Gateway benchmark report from real GPU runs.
