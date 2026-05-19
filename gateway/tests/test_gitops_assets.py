from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GITOPS_DIR = ROOT / "deploy/gitops"
CONTAINER_WORKFLOW_PATH = ROOT / ".github/workflows/container.yml"
GITOPS_DOC_PATH = ROOT / "docs/gitops_deployment.md"


def read_gitops_file(name: str) -> str:
    return (GITOPS_DIR / name).read_text(encoding="utf-8")


def test_argocd_applications_sync_the_helm_chart_from_git() -> None:
    for manifest_name in [
        "argocd-application-mock.yaml",
        "argocd-application-vllm.yaml",
    ]:
        manifest = read_gitops_file(manifest_name)

        assert "apiVersion: argoproj.io/v1alpha1" in manifest
        assert "kind: Application" in manifest
        assert "namespace: argocd" in manifest
        assert "repoURL: https://github.com/ictup/Mini_LLM_Serving_Platform.git" in manifest
        assert "targetRevision: main" in manifest
        assert "path: deploy/helm" in manifest
        assert "releaseName: mini-llm" in manifest
        assert "server: https://kubernetes.default.svc" in manifest
        assert "namespace: mini-llm-serving" in manifest
        assert "prune: true" in manifest
        assert "selfHeal: true" in manifest
        assert "CreateNamespace=true" in manifest


def test_gitops_mock_application_uses_published_gateway_image() -> None:
    manifest = read_gitops_file("argocd-application-mock.yaml")

    assert "name: mini-llm-serving-mock" in manifest
    assert "ghcr.io/ictup/mini-llm-serving-platform:main" in manifest
    assert "existingSecretName: gateway-secret" in manifest
    assert "mockBackend:" in manifest
    assert "enabled: true" in manifest
    assert "vllm:" in manifest
    assert "enabled: false" in manifest


def test_gitops_vllm_application_uses_external_secrets_and_gpu_values() -> None:
    manifest = read_gitops_file("argocd-application-vllm.yaml")

    assert "name: mini-llm-serving-vllm" in manifest
    assert "existingSecretName: gateway-secret" in manifest
    assert "existingSecretName: vllm-secret" in manifest
    assert "mockBackend:" in manifest
    assert "enabled: false" in manifest
    assert "vllm:" in manifest
    assert "enabled: true" in manifest
    assert "vllm/vllm-openai:v0.8.5.post1" in manifest
    assert "model: Qwen/Qwen2.5-0.5B-Instruct" in manifest
    assert "gpu: 1" in manifest
    assert "tokenizerProfilesJson:" in manifest
    assert "dcgmExporter:" in manifest


def test_container_workflow_publishes_gateway_image_to_ghcr() -> None:
    workflow = CONTAINER_WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "packages: write" in workflow
    assert "docker/login-action@v3" in workflow
    assert "docker/metadata-action@v5" in workflow
    assert "docker/build-push-action@v6" in workflow
    assert "ghcr.io/${{ github.repository_owner }}/mini-llm-serving-platform" in workflow
    assert "file: Dockerfile.gateway" in workflow
    assert "push: true" in workflow
    assert "type=raw,value=main" in workflow
    assert "type=ref,event=tag" in workflow


def test_gitops_documentation_references_secrets_and_validation() -> None:
    doc = GITOPS_DOC_PATH.read_text(encoding="utf-8")

    assert "gateway-secret" in doc
    assert "vllm-secret" in doc
    assert "argocd app sync mini-llm-serving-mock" in doc
    assert "argocd app sync mini-llm-serving-vllm" in doc
    assert "curl http://localhost:9090/api/v1/rules" in doc
