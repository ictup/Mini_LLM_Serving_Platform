from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HELM_DIR = ROOT / "deploy/helm"
TEMPLATES_DIR = HELM_DIR / "templates"


def read_chart_file(name: str) -> str:
    return (HELM_DIR / name).read_text(encoding="utf-8")


def read_template(name: str) -> str:
    return (TEMPLATES_DIR / name).read_text(encoding="utf-8")


def test_helm_chart_has_expected_metadata_and_values() -> None:
    chart = read_chart_file("Chart.yaml")
    values = read_chart_file("values.yaml")

    assert "name: mini-llm-serving-platform" in chart
    assert "type: application" in chart
    assert "gateway:" in values
    assert "tpm: 60000" in values
    assert "concurrentRequests: 20" in values
    assert "defaultCompletionTokens: 256" in values
    assert "tokenizerProfilesJson:" in values
    assert "tokenizerPathsJson:" in values
    assert "maxBodyBytes: 1048576" in values
    assert "maxChatMessages: 64" in values
    assert "maxChatMessageChars: 16000" in values
    assert "maxChatTotalMessageChars: 64000" in values
    assert "existingSecretName: \"\"" in values
    assert "ingress:" in values
    assert "autoscaling:" in values
    assert "targetCPUUtilizationPercentage: 70" in values
    assert "startupProbe:" in values
    assert "mockBackend:" in values
    assert "redis:" in values
    assert "prometheus:" in values
    assert "alerting:" in values
    assert "gatewayHighErrorRatio: 0.05" in values
    assert "vllmKvCacheUsagePercent: 85" in values
    assert "dcgmExporter:" in values
    assert "nvcr.io/nvidia/k8s/dcgm-exporter:3.3.9-3.6.1-ubuntu22.04" in values
    assert "vllm:" in values
    assert "enabled: false" in values
    assert "Qwen/Qwen2.5-0.5B-Instruct" in values
    assert "modelRoutesJson: '{}'" in values


def test_gitops_directory_documents_argocd_entrypoints() -> None:
    gitops_readme = (ROOT / "deploy/gitops/README.md").read_text(encoding="utf-8")

    assert "argocd-application-mock.yaml" in gitops_readme
    assert "argocd-application-vllm.yaml" in gitops_readme
    assert "ghcr.io/ictup/mini-llm-serving-platform:main" in gitops_readme
    assert "gateway-secret" in gitops_readme


def test_helm_gateway_template_preserves_health_and_ready_probes() -> None:
    deployment = read_template("gateway-deployment.yaml")
    config = read_template("gateway-config.yaml")
    secret = read_template("gateway-secret.yaml")

    assert "path: /health" in deployment
    assert "path: /ready" in deployment
    assert "name: gateway-config" in deployment
    assert "mini-llm.gatewaySecretName" in deployment
    assert "resources:" in deployment
    assert "toYaml .Values.gateway.resources" in deployment
    assert "BACKEND_TYPE: mock" in config
    assert "BACKEND_TYPE: vllm" in config
    assert "RATE_LIMIT_TPM:" in config
    assert "RATE_LIMIT_CONCURRENT_REQUESTS:" in config
    assert "RATE_LIMIT_DEFAULT_COMPLETION_TOKENS:" in config
    assert "RATE_LIMIT_TOKENIZER_PROFILES_JSON:" in config
    assert "RATE_LIMIT_TOKENIZER_PATHS_JSON:" in config
    assert 'printf "{\\"qwen-small\\":\\"qwen2\\",\\"%s\\":\\"qwen2\\"}"' in config
    assert "MAX_REQUEST_BODY_BYTES:" in config
    assert "MAX_CHAT_MESSAGES:" in config
    assert "MAX_CHAT_MESSAGE_CHARS:" in config
    assert "MAX_CHAT_TOTAL_MESSAGE_CHARS:" in config
    assert "VLLM_BASE_URL: http://vllm:" in config
    assert "MODEL_ROUTES_JSON:" in config
    assert "API_KEYS:" in secret
    assert "VLLM_API_KEY:" in secret


def test_helm_chart_templates_optional_vllm_backend() -> None:
    vllm = read_template("vllm.yaml")
    prometheus = read_template("prometheus.yaml")
    dcgm = read_template("dcgm-exporter.yaml")

    assert "{{- if .Values.vllm.enabled }}" in vllm
    assert "image: {{ .Values.vllm.image | quote }}" in vllm
    assert "- $(VLLM_MODEL)" in vllm
    assert "- $(VLLM_API_KEY)" in vllm
    assert "nvidia.com/gpu: {{ .Values.vllm.gpu | quote }}" in vllm
    assert "startupProbe:" in vllm
    assert "mini-llm.vllmSecretName" in vllm
    assert "--disable-frontend-multiprocessing" in vllm
    assert "job_name: vllm" in prometheus
    assert "vllm:{{ .Values.vllm.service.port }}" in prometheus
    assert "{{- if .Values.dcgmExporter.enabled }}" in dcgm
    assert "kind: DaemonSet" in dcgm
    assert "dcgm-exporter" in dcgm
    assert "nvidia.com/gpu: {{ .Values.dcgmExporter.gpu | quote }}" in dcgm
    assert "job_name: dcgm-exporter" in prometheus
    assert "dcgm-exporter:{{ .Values.dcgmExporter.service.port }}" in prometheus


def test_helm_chart_templates_ingress_hpa_and_external_secrets() -> None:
    ingress = read_template("gateway-ingress.yaml")
    hpa = read_template("gateway-hpa.yaml")
    secret = read_template("gateway-secret.yaml")
    helpers = read_template("_helpers.tpl")

    assert "{{- if .Values.gateway.ingress.enabled }}" in ingress
    assert "kind: Ingress" in ingress
    assert "tlsSecretName" in ingress
    assert "{{- if .Values.gateway.autoscaling.enabled }}" in hpa
    assert "kind: HorizontalPodAutoscaler" in hpa
    assert "targetCPUUtilizationPercentage" in hpa
    assert "{{- if not .Values.gateway.existingSecretName }}" in secret
    assert "mini-llm.gatewaySecretName" in helpers
    assert "mini-llm.vllmSecretName" in helpers


def test_helm_chart_templates_mock_backend_redis_and_prometheus() -> None:
    mock_backend = read_template("mock-backend.yaml")
    redis = read_template("redis.yaml")
    prometheus = read_template("prometheus.yaml")

    assert "{{- if .Values.mockBackend.enabled }}" in mock_backend
    assert "serving.mock_backend.app:app" in mock_backend
    assert "{{- if .Values.redis.enabled }}" in redis
    assert "redis-cli" in redis
    assert "{{- if .Values.prometheus.enabled }}" in prometheus
    assert "gateway:{{ .Values.gateway.service.port }}" in prometheus
    assert "evaluation_interval: {{ .Values.prometheus.evaluationInterval }}" in prometheus
    assert "/etc/prometheus/alerts.yml" in prometheus
    assert "alert: GatewayHighErrorRate" in prometheus
    assert "alert: VLLMHighKVCacheUsage" in prometheus
    assert "mountPath: /etc/prometheus/alerts.yml" in prometheus
