import json
import sys

from scripts.local_e2e import LocalE2EConfig, build_gateway_env, build_smoke_command


def test_build_gateway_env_routes_requested_alias_to_mock_backend() -> None:
    config = LocalE2EConfig(
        host="127.0.0.1",
        gateway_port=18080,
        mock_port=19000,
        api_key="test-key",
        model="qwen-small",
        timeout_seconds=5,
        skip_streaming=False,
    )

    env = build_gateway_env(config, base_env={"EXISTING": "1"})

    assert env["EXISTING"] == "1"
    assert env["ENV"] == "local-e2e"
    assert env["API_KEYS"] == "test-key"
    assert env["RATE_LIMIT_ENABLED"] == "false"
    assert env["BACKEND_TYPE"] == "mock"
    assert env["MOCK_BASE_URL"] == "http://127.0.0.1:19000/v1"
    assert env["DEFAULT_MODEL"] == "qwen-small"
    assert json.loads(env["MODEL_ALIASES_JSON"]) == {
        "mock": "mock",
        "qwen-small": "mock",
    }


def test_build_smoke_command_uses_gateway_base_url_and_skip_streaming_flag() -> None:
    config = LocalE2EConfig(
        host="127.0.0.1",
        gateway_port=18080,
        mock_port=19000,
        api_key="test-key",
        model="mock",
        timeout_seconds=5,
        skip_streaming=True,
    )

    command = build_smoke_command(config)

    assert command[0] == sys.executable
    assert command[-1] == "--skip-streaming"
    assert "--base-url" in command
    assert "http://127.0.0.1:18080/v1" in command
    assert "--api-key" in command
    assert "test-key" in command
    assert "--model" in command
    assert "mock" in command
