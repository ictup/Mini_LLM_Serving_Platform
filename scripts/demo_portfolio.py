import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class DemoArtifact:
    label: str
    path: str
    purpose: str


STACK_ARTIFACTS = [
    DemoArtifact("FastAPI Gateway", "gateway/app/main.py", "OpenAI-compatible API surface"),
    DemoArtifact("OpenAI schemas", "gateway/app/schemas/openai.py", "client contract"),
    DemoArtifact("Redis rate limits", "gateway/app/core/rate_limit.py", "RPM, TPM, concurrency"),
    DemoArtifact(
        "Model routing",
        "gateway/app/proxy/model_aliases.py",
        "aliases, weights, fallback",
    ),
    DemoArtifact("Mock backend", "serving/mock_backend/app.py", "no-GPU CI and demo path"),
    DemoArtifact("Benchmark runner", "benchmark/run_benchmark.py", "RPS, TTFT, TPOT, p95/p99"),
    DemoArtifact("Prometheus metrics", "gateway/app/observability/metrics.py", "Gateway telemetry"),
    DemoArtifact("Grafana dashboards", "monitoring/grafana/dashboards", "Gateway, vLLM, GPU views"),
    DemoArtifact("Docker GPU stack", "docker-compose.gpu.yml", "vLLM and DCGM local path"),
    DemoArtifact("Kubernetes overlay", "deploy/k8s-gpu", "vLLM and GPU telemetry manifests"),
    DemoArtifact("Helm chart", "deploy/helm", "parameterized deployment"),
    DemoArtifact("Argo CD GitOps", "deploy/gitops", "continuous delivery examples"),
    DemoArtifact("Terraform IaC", "deploy/terraform", "cluster entry-point skeleton"),
    DemoArtifact("Security workflow", ".github/workflows/security.yml", "audit, Trivy, SBOM"),
]


DEMO_COMMANDS = {
    "mock": [
        "uv run python scripts/demo_portfolio.py --execute-local",
        "uv run python scripts/local_e2e.py --gateway-port 18080 --mock-port 19000",
        "uv run python benchmark/client_smoke_test.py",
    ],
    "gpu": [
        '$env:VLLM_MODEL="Qwen/Qwen2.5-0.5B-Instruct"',
        '$env:VLLM_IMAGE_TAG="v0.8.5.post1"',
        "docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build",
        "uv run python scripts/warmup_gateway.py --model qwen-small",
        "uv run python benchmark/client_smoke_test.py --model qwen-small",
    ],
    "benchmark": [
        "uv run python benchmark/run_benchmark.py --profile portfolio "
        "--base-url http://localhost:8080/v1 --api-key dev-key --model qwen-small "
        "--prompts benchmark/prompts/short_prompts.jsonl --timeout-seconds 120 "
        "--stream true",
        "uv run python benchmark/collect_prometheus_snapshot.py --prometheus-url http://localhost:9090",
        "uv run python benchmark/sample_prometheus_timeseries.py "
        "--prometheus-url http://localhost:9090 --duration-seconds 180 --interval-seconds 5",
    ],
    "infra": [
        "kubectl kustomize deploy/k8s",
        "kubectl kustomize deploy/k8s-gpu",
        "helm lint deploy/helm",
        "helm template mini-llm deploy/helm --namespace mini-llm-serving "
        "--set vllm.enabled=true --set mockBackend.enabled=false "
        "--set dcgmExporter.enabled=true",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Portfolio demo controller for the LLM serving gateway."
    )
    parser.add_argument(
        "--profile",
        choices=("all", "mock", "gpu", "benchmark", "infra"),
        default="all",
        help="Demo segment to print.",
    )
    parser.add_argument(
        "--execute-local",
        action="store_true",
        help="Run the no-GPU local end-to-end demo after printing the walkthrough.",
    )
    parser.add_argument(
        "--gateway-port",
        type=int,
        default=18080,
        help="Gateway port used when --execute-local is set.",
    )
    parser.add_argument(
        "--mock-port",
        type=int,
        default=19000,
        help="Mock backend port used when --execute-local is set.",
    )
    parser.add_argument(
        "--skip-streaming",
        action="store_true",
        help="Pass --skip-streaming to scripts/local_e2e.py when --execute-local is used.",
    )
    return parser.parse_args()


def print_header(title: str) -> None:
    print()
    print("=" * len(title))
    print(title)
    print("=" * len(title))


def print_artifacts() -> None:
    print_header("OpenAI-Compatible LLM Serving Gateway")
    print(
        "Demo goal: prove that this repository is an LLM serving platform, "
        "not only a model API wrapper."
    )
    print()
    for artifact in STACK_ARTIFACTS:
        status = "ok" if (ROOT / artifact.path).exists() else "missing"
        print(f"[{status}] {artifact.label}: {artifact.path} - {artifact.purpose}")


def print_commands(profile: str) -> None:
    selected_profiles = ("mock", "gpu", "benchmark", "infra") if profile == "all" else (profile,)

    for selected_profile in selected_profiles:
        print_header(f"{selected_profile.title()} demo commands")
        for command in DEMO_COMMANDS[selected_profile]:
            print(f"$ {command}")


def print_talking_points() -> None:
    print_header("Talking points")
    points = [
        "The Gateway preserves OpenAI compatibility while owning auth, quotas, "
        "routing, and metrics.",
        "The mock backend keeps CI and laptop demos reproducible without CUDA or model downloads.",
        "The vLLM path demonstrates real GPU serving behind the same client contract.",
        "Redis-backed RPM, TPM, and concurrency limits show operational policy around inference.",
        "Prometheus, Grafana, vLLM metrics, and DCGM telemetry show serving "
        "behavior beyond app logs.",
        "Benchmarks report tail latency, TTFT, TPOT, output tokens/sec, and error rate.",
        "Kubernetes, Helm, Argo CD, Terraform, CI, Trivy, SBOM, and release "
        "workflows show delivery maturity.",
    ]
    for index, point in enumerate(points, start=1):
        print(f"{index}. {point}")


def run_local_e2e(skip_streaming: bool, gateway_port: int, mock_port: int) -> None:
    print_header("Executing no-GPU local demo")
    sys.stdout.flush()
    command = [
        sys.executable,
        str(ROOT / "scripts" / "local_e2e.py"),
        "--gateway-port",
        str(gateway_port),
        "--mock-port",
        str(mock_port),
    ]
    if skip_streaming:
        command.append("--skip-streaming")
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    args = parse_args()
    print_artifacts()
    print_commands(args.profile)
    print_talking_points()

    if args.execute_local:
        run_local_e2e(args.skip_streaming, args.gateway_port, args.mock_port)


if __name__ == "__main__":
    main()
