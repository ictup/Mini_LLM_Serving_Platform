from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
K8S_DIR = ROOT / "deploy/k8s"
K8S_GPU_DIR = ROOT / "deploy/k8s-gpu"


def read_manifest(name: str) -> str:
    return (K8S_DIR / name).read_text(encoding="utf-8")


def read_gpu_manifest(name: str) -> str:
    return (K8S_GPU_DIR / name).read_text(encoding="utf-8")


def test_kustomization_lists_no_gpu_stack_resources() -> None:
    kustomization = read_manifest("kustomization.yaml")

    for resource in [
        "namespace.yaml",
        "gateway-config.yaml",
        "gateway-secret.yaml",
        "gateway-deployment.yaml",
        "gateway-service.yaml",
        "mock-backend-deployment.yaml",
        "mock-backend-service.yaml",
        "redis-deployment.yaml",
        "redis-service.yaml",
        "prometheus-config.yaml",
        "prometheus-deployment.yaml",
        "prometheus-service.yaml",
    ]:
        assert f"- {resource}" in kustomization


def test_gateway_k8s_manifest_uses_ready_and_health_probes() -> None:
    manifest = read_manifest("gateway-deployment.yaml")

    assert "kind: Deployment" in manifest
    assert "name: gateway" in manifest
    assert "image: mini-llm-serving-platform:local" in manifest
    assert "path: /health" in manifest
    assert "path: /ready" in manifest
    assert "name: gateway-config" in manifest
    assert "name: gateway-secret" in manifest


def test_gateway_k8s_config_points_to_cluster_services() -> None:
    manifest = read_manifest("gateway-config.yaml")

    assert "REDIS_URL: redis://redis:6379/0" in manifest
    assert 'RATE_LIMIT_TPM: "60000"' in manifest
    assert 'RATE_LIMIT_DEFAULT_COMPLETION_TOKENS: "256"' in manifest
    assert "MOCK_BASE_URL: http://mock-backend:9000/v1" in manifest
    assert "BACKEND_TYPE: mock" in manifest
    assert """MODEL_ALIASES_JSON: '{"mock":"mock","qwen-small":"mock"}'""" in manifest


def test_mock_backend_and_redis_services_have_expected_ports() -> None:
    mock_backend = read_manifest("mock-backend-service.yaml")
    redis = read_manifest("redis-service.yaml")

    assert "name: mock-backend" in mock_backend
    assert "port: 9000" in mock_backend
    assert "targetPort: http" in mock_backend
    assert "name: redis" in redis
    assert "port: 6379" in redis
    assert "targetPort: redis" in redis


def test_prometheus_k8s_config_scrapes_gateway_metrics() -> None:
    config = read_manifest("prometheus-config.yaml")
    deployment = read_manifest("prometheus-deployment.yaml")

    assert "job_name: gateway" in config
    assert "metrics_path: /metrics" in config
    assert "gateway:8080" in config
    assert "mountPath: /etc/prometheus/prometheus.yml" in deployment
    assert "path: /-/ready" in deployment


def test_gpu_kustomization_reuses_base_and_adds_vllm_resources() -> None:
    kustomization = read_gpu_manifest("kustomization.yaml")

    assert "- ../k8s" in kustomization
    assert "- vllm-config.yaml" in kustomization
    assert "- vllm-secret.yaml" in kustomization
    assert "- vllm-deployment.yaml" in kustomization
    assert "- vllm-service.yaml" in kustomization
    assert "gateway-config-patch.yaml" in kustomization
    assert "prometheus-config-patch.yaml" in kustomization


def test_gpu_gateway_patch_switches_gateway_to_vllm() -> None:
    manifest = read_gpu_manifest("gateway-config-patch.yaml")
    secret = read_gpu_manifest("gateway-secret-patch.yaml")

    assert "BACKEND_TYPE: vllm" in manifest
    assert "VLLM_BASE_URL: http://vllm:8000/v1" in manifest
    assert "DEFAULT_MODEL: qwen-small" in manifest
    assert """MODEL_ALIASES_JSON: '{"qwen-small":"Qwen/Qwen2.5-1.5B-Instruct"}'""" in manifest
    assert "VLLM_API_KEY: local-vllm-key" in secret


def test_vllm_k8s_manifest_requests_gpu_and_exposes_service() -> None:
    deployment = read_gpu_manifest("vllm-deployment.yaml")
    service = read_gpu_manifest("vllm-service.yaml")

    assert "image: vllm/vllm-openai:latest" in deployment
    assert "nvidia.com/gpu: \"1\"" in deployment
    assert "- --model" in deployment
    assert "- $(VLLM_MODEL)" in deployment
    assert "- --api-key" in deployment
    assert "- $(VLLM_API_KEY)" in deployment
    assert "path: /health" in deployment
    assert "name: vllm" in service
    assert "port: 8000" in service


def test_gpu_prometheus_patch_scrapes_vllm_metrics() -> None:
    manifest = read_gpu_manifest("prometheus-config-patch.yaml")

    assert "job_name: gateway" in manifest
    assert "job_name: vllm" in manifest
    assert "vllm:8000" in manifest
