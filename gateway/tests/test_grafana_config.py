import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_PATH = ROOT / "monitoring/grafana/dashboards/gateway-overview.json"
VLLM_DASHBOARD_PATH = ROOT / "monitoring/grafana/dashboards/vllm-engine-overview.json"
DATASOURCE_PATH = ROOT / "monitoring/grafana/provisioning/datasources/prometheus.yml"
PROVIDER_PATH = ROOT / "monitoring/grafana/provisioning/dashboards/gateway.yml"
PROMETHEUS_GPU_PATH = ROOT / "monitoring/prometheus/prometheus.gpu.yml"
DOCKER_COMPOSE_PATH = ROOT / "docker-compose.yml"
DOCKER_COMPOSE_GPU_PATH = ROOT / "docker-compose.gpu.yml"


def test_grafana_dashboard_json_references_gateway_metrics() -> None:
    dashboard = json.loads(DASHBOARD_PATH.read_text(encoding="utf-8"))
    expressions = [
        target["expr"]
        for panel in dashboard["panels"]
        for target in panel.get("targets", [])
        if "expr" in target
    ]

    assert dashboard["uid"] == "gateway-overview"
    assert dashboard["title"] == "Gateway Overview"
    assert len(dashboard["panels"]) == 9
    assert any("gateway_http_requests_total" in expression for expression in expressions)
    assert any("gateway_http_errors_total" in expression for expression in expressions)
    assert any(
        "gateway_http_request_duration_seconds_bucket" in expression
        for expression in expressions
    )
    assert any("gateway_stream_ttft_seconds_bucket" in expression for expression in expressions)
    assert any(
        "gateway_stream_duration_seconds_bucket" in expression
        for expression in expressions
    )
    assert any(
        "gateway_stream_output_chunks_total" in expression for expression in expressions
    )
    assert any("gateway_http_rejections_total" in expression for expression in expressions)


def test_grafana_provisioning_uses_prometheus_uid_and_dashboard_path() -> None:
    datasource_config = DATASOURCE_PATH.read_text(encoding="utf-8")
    provider_config = PROVIDER_PATH.read_text(encoding="utf-8")

    assert "uid: prometheus" in datasource_config
    assert "url: http://prometheus:9090" in datasource_config
    assert "path: /var/lib/grafana/dashboards" in provider_config


def test_vllm_dashboard_json_references_vllm_engine_metrics() -> None:
    dashboard = json.loads(VLLM_DASHBOARD_PATH.read_text(encoding="utf-8"))
    expressions = [
        target["expr"]
        for panel in dashboard["panels"]
        for target in panel.get("targets", [])
        if "expr" in target
    ]

    assert dashboard["uid"] == "vllm-engine-overview"
    assert dashboard["title"] == "vLLM Engine Overview"
    assert len(dashboard["panels"]) == 6
    assert any("vllm:num_requests_running" in expression for expression in expressions)
    assert any("vllm:kv_cache_usage_perc" in expression for expression in expressions)
    assert any(
        "vllm:time_to_first_token_seconds_bucket" in expression
        for expression in expressions
    )
    assert any(
        "vllm:e2e_request_latency_seconds_bucket" in expression
        for expression in expressions
    )
    assert any(
        "vllm:inter_token_latency_seconds_bucket" in expression
        for expression in expressions
    )
    assert any("vllm:generation_tokens_total" in expression for expression in expressions)


def test_gpu_prometheus_config_scrapes_vllm() -> None:
    prometheus_gpu_config = PROMETHEUS_GPU_PATH.read_text(encoding="utf-8")

    assert "job_name: gateway" in prometheus_gpu_config
    assert "job_name: vllm" in prometheus_gpu_config
    assert "vllm:8000" in prometheus_gpu_config


def test_docker_compose_persists_grafana_state() -> None:
    compose = DOCKER_COMPOSE_PATH.read_text(encoding="utf-8")

    assert "grafana-data:/var/lib/grafana" in compose
    assert "volumes:" in compose
    assert "grafana-data:" in compose


def test_gpu_compose_waits_for_vllm_healthcheck() -> None:
    compose = DOCKER_COMPOSE_GPU_PATH.read_text(encoding="utf-8")

    assert "condition: service_healthy" in compose
    assert "healthcheck:" in compose
    assert "http://127.0.0.1:8000/health" in compose
