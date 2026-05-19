import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class LocalE2EConfig:
    host: str
    gateway_port: int
    mock_port: int
    api_key: str
    model: str
    smoke_script: str
    timeout_seconds: float
    skip_streaming: bool

    @property
    def gateway_base_url(self) -> str:
        return f"http://{self.host}:{self.gateway_port}/v1"

    @property
    def mock_base_url(self) -> str:
        return f"http://{self.host}:{self.mock_port}/v1"


def parse_args() -> LocalE2EConfig:
    parser = argparse.ArgumentParser(
        description="Start the local mock backend and Gateway, then run the SDK smoke test."
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host used for both services.")
    parser.add_argument("--gateway-port", type=int, default=8080, help="Gateway port.")
    parser.add_argument("--mock-port", type=int, default=9000, help="Mock backend port.")
    parser.add_argument(
        "--api-key",
        default=os.getenv("OPENAI_API_KEY", "dev-key"),
        help="API key configured on the Gateway and used by the smoke test.",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("LLM_MODEL", "mock"),
        help="Client-facing model alias used by the smoke test.",
    )
    parser.add_argument(
        "--smoke-script",
        default="benchmark/client_smoke_test.py",
        help="Smoke script to run after Gateway readiness. Must live under the repository root.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=30,
        help="Maximum seconds to wait for each service to become ready.",
    )
    parser.add_argument(
        "--skip-streaming",
        action="store_true",
        help="Run only the non-streaming smoke test.",
    )
    args = parser.parse_args()
    return LocalE2EConfig(
        host=args.host,
        gateway_port=args.gateway_port,
        mock_port=args.mock_port,
        api_key=args.api_key,
        model=args.model,
        smoke_script=args.smoke_script,
        timeout_seconds=args.timeout_seconds,
        skip_streaming=args.skip_streaming,
    )


def build_gateway_env(
    config: LocalE2EConfig,
    base_env: Mapping[str, str] | None = None,
) -> dict[str, str]:
    env = dict(base_env or os.environ)
    model_aliases = {"mock": "mock", config.model: "mock"}
    env.update(
        {
            "APP_NAME": "mini-llm-serving-platform",
            "ENV": "local-e2e",
            "LOG_LEVEL": "INFO",
            "API_KEYS": config.api_key,
            "RATE_LIMIT_ENABLED": "false",
            "BACKEND_TYPE": "mock",
            "MOCK_BASE_URL": config.mock_base_url,
            "DEFAULT_MODEL": config.model,
            "MODEL_ALIASES_JSON": json.dumps(model_aliases, separators=(",", ":")),
            "METRICS_ENABLED": "true",
        }
    )
    return env


def build_smoke_command(config: LocalE2EConfig) -> list[str]:
    command = [
        sys.executable,
        str(resolve_repo_path(config.smoke_script)),
        "--base-url",
        config.gateway_base_url,
        "--api-key",
        config.api_key,
        "--model",
        config.model,
    ]
    if config.skip_streaming:
        command.append("--skip-streaming")
    return command


def resolve_repo_path(path: str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate

    resolved = candidate.resolve()
    if not resolved.is_relative_to(ROOT):
        raise ValueError(f"path must stay under repository root: {path}")
    return resolved


def ensure_port_available(host: str, port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        result = sock.connect_ex((host, port))
    if result == 0:
        raise RuntimeError(f"{host}:{port} is already in use")


def start_uvicorn(app: str, host: str, port: int, env: Mapping[str, str]) -> subprocess.Popen[str]:
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        app,
        "--host",
        host,
        "--port",
        str(port),
    ]
    return subprocess.Popen(
        command,
        cwd=ROOT,
        env=dict(env),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def wait_for_http(
    url: str,
    timeout_seconds: float,
    process: subprocess.Popen[str],
    process_name: str,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error = ""

    while time.monotonic() < deadline:
        if process.poll() is not None:
            output = collect_process_output(process)
            raise RuntimeError(f"{process_name} exited before becoming ready.\n{output}")

        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
                last_error = f"status={response.status}"
        except (TimeoutError, OSError, urllib.error.URLError) as exc:
            last_error = str(exc)

        time.sleep(0.25)

    raise TimeoutError(f"timed out waiting for {process_name} at {url}: {last_error}")


def collect_process_output(process: subprocess.Popen[str]) -> str:
    if process.stdout is None:
        return ""
    try:
        output, _ = process.communicate(timeout=1)
    except subprocess.TimeoutExpired:
        return ""
    return output[-4000:].strip()


def stop_process(process: subprocess.Popen[str], name: str) -> None:
    if process.poll() is not None:
        return

    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
    print(f"stopped {name}")


def run_smoke_test(config: LocalE2EConfig) -> None:
    result = subprocess.run(
        build_smoke_command(config),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"smoke test failed with exit code {result.returncode}")


def main() -> None:
    config = parse_args()
    ensure_port_available(config.host, config.mock_port)
    ensure_port_available(config.host, config.gateway_port)

    processes: list[tuple[str, subprocess.Popen[str]]] = []
    try:
        print(f"starting mock backend on {config.host}:{config.mock_port}")
        mock_process = start_uvicorn(
            "serving.mock_backend.app:app",
            config.host,
            config.mock_port,
            os.environ,
        )
        processes.append(("mock backend", mock_process))
        wait_for_http(
            f"{config.mock_base_url}/models",
            config.timeout_seconds,
            mock_process,
            "mock backend",
        )

        print(f"starting gateway on {config.host}:{config.gateway_port}")
        gateway_process = start_uvicorn(
            "gateway.app.main:app",
            config.host,
            config.gateway_port,
            build_gateway_env(config),
        )
        processes.append(("gateway", gateway_process))
        wait_for_http(
            f"http://{config.host}:{config.gateway_port}/ready",
            config.timeout_seconds,
            gateway_process,
            "gateway",
        )

        print("running OpenAI SDK smoke test")
        run_smoke_test(config)
        print("local e2e smoke test passed")
    finally:
        for name, process in reversed(processes):
            stop_process(process, name)


if __name__ == "__main__":
    main()
