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
    assert "mockBackend:" in values
    assert "redis:" in values
    assert "prometheus:" in values
    assert "vllm:" in values
    assert "enabled: false" in values
    assert "Qwen/Qwen2.5-1.5B-Instruct" in values


def test_helm_gateway_template_preserves_health_and_ready_probes() -> None:
    deployment = read_template("gateway-deployment.yaml")
    config = read_template("gateway-config.yaml")
    secret = read_template("gateway-secret.yaml")

    assert "path: /health" in deployment
    assert "path: /ready" in deployment
    assert "name: gateway-config" in deployment
    assert "name: gateway-secret" in deployment
    assert "BACKEND_TYPE: mock" in config
    assert "BACKEND_TYPE: vllm" in config
    assert "RATE_LIMIT_TPM:" in config
    assert "RATE_LIMIT_CONCURRENT_REQUESTS:" in config
    assert "RATE_LIMIT_DEFAULT_COMPLETION_TOKENS:" in config
    assert "VLLM_BASE_URL: http://vllm:" in config
    assert "API_KEYS:" in secret
    assert "VLLM_API_KEY:" in secret


def test_helm_chart_templates_optional_vllm_backend() -> None:
    vllm = read_template("vllm.yaml")
    prometheus = read_template("prometheus.yaml")

    assert "{{- if .Values.vllm.enabled }}" in vllm
    assert "image: {{ .Values.vllm.image | quote }}" in vllm
    assert "- $(VLLM_MODEL)" in vllm
    assert "- $(VLLM_API_KEY)" in vllm
    assert "nvidia.com/gpu: {{ .Values.vllm.gpu | quote }}" in vllm
    assert "job_name: vllm" in prometheus
    assert "vllm:{{ .Values.vllm.service.port }}" in prometheus


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
