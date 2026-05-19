from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SECURITY_WORKFLOW_PATH = ROOT / ".github/workflows/security.yml"
CONTAINER_WORKFLOW_PATH = ROOT / ".github/workflows/container.yml"
DEPENDABOT_PATH = ROOT / ".github/dependabot.yml"
SECURITY_DOC_PATH = ROOT / "docs/security.md"


def test_security_workflow_runs_dependency_audit_and_trivy_scans() -> None:
    workflow = SECURITY_WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "name: Security" in workflow
    assert "pull_request:" in workflow
    assert "schedule:" in workflow
    assert "security-events: write" in workflow
    assert "uv run --with pip-audit pip-audit --strict" in workflow
    assert "aquasecurity/trivy-action@0.28.0" in workflow
    assert "scanners: vuln,secret,misconfig" in workflow
    assert "github/codeql-action/upload-sarif@v3" in workflow
    assert "docker/build-push-action@v6" in workflow
    assert "format: cyclonedx" in workflow
    assert "actions/upload-artifact@v4" in workflow
    assert "sbom-cyclonedx.json" in workflow


def test_security_workflow_scans_repository_and_container_image() -> None:
    workflow = SECURITY_WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "scan-type: fs" in workflow
    assert "scan-ref: ." in workflow
    assert "output: trivy-repository.sarif" in workflow
    assert "image-ref: mini-llm-serving-platform:security-scan" in workflow
    assert "output: trivy-image.sarif" in workflow
    assert "severity: HIGH,CRITICAL" in workflow
    assert 'exit-code: "0"' in workflow


def test_container_workflow_publishes_attestations() -> None:
    workflow = CONTAINER_WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "provenance: true" in workflow
    assert "sbom: true" in workflow
    assert "docker/metadata-action@v5" in workflow
    assert "type=sha,prefix=sha-" in workflow


def test_dependabot_tracks_actions_python_and_docker_updates() -> None:
    config = DEPENDABOT_PATH.read_text(encoding="utf-8")

    assert "package-ecosystem: github-actions" in config
    assert "package-ecosystem: pip" in config
    assert "package-ecosystem: docker" in config
    assert "interval: weekly" in config
    assert "open-pull-requests-limit: 5" in config


def test_security_documentation_covers_local_and_production_workflows() -> None:
    doc = SECURITY_DOC_PATH.read_text(encoding="utf-8")

    assert "pip-audit" in doc
    assert "trivy image" in doc
    assert "trivy fs" in doc
    assert "CycloneDX SBOM" in doc
    assert "SARIF" in doc
    assert "Terraform placeholder Secrets" in doc
