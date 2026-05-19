from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ALERT_RULES_PATH = ROOT / "monitoring/prometheus/alerts.yml"
PROMETHEUS_PATH = ROOT / "monitoring/prometheus/prometheus.yml"
PROMETHEUS_GPU_PATH = ROOT / "monitoring/prometheus/prometheus.gpu.yml"
DOCKER_COMPOSE_PATH = ROOT / "docker-compose.yml"


def test_prometheus_alert_rules_cover_gateway_and_vllm_risks() -> None:
    rules = ALERT_RULES_PATH.read_text(encoding="utf-8")

    for alert_name in [
        "GatewayHighErrorRate",
        "GatewayHighP95Latency",
        "GatewayHighP95TTFT",
        "GatewayHighRejectionRate",
        "VLLMWaitingRequests",
        "VLLMHighKVCacheUsage",
        "VLLMHighP95TTFT",
    ]:
        assert f"alert: {alert_name}" in rules

    for metric_name in [
        "gateway_http_errors_total",
        "gateway_http_request_duration_seconds_bucket",
        "gateway_stream_ttft_seconds_bucket",
        "gateway_http_rejections_total",
        "vllm:num_requests_waiting",
        "vllm:kv_cache_usage_perc",
        "vllm:gpu_cache_usage_perc",
        "vllm:time_to_first_token_seconds_bucket",
    ]:
        assert metric_name in rules


def test_prometheus_configs_load_alert_rule_file() -> None:
    for config_path in [PROMETHEUS_PATH, PROMETHEUS_GPU_PATH]:
        config = config_path.read_text(encoding="utf-8")

        assert "evaluation_interval: 30s" in config
        assert "rule_files:" in config
        assert "- /etc/prometheus/alerts.yml" in config


def test_docker_compose_mounts_prometheus_alert_rules() -> None:
    compose = DOCKER_COMPOSE_PATH.read_text(encoding="utf-8")

    assert "./monitoring/prometheus/alerts.yml:/etc/prometheus/alerts.yml:ro" in compose
