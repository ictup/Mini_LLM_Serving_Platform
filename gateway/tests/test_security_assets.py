from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SECURITY_WORKFLOW_PATH = ROOT / ".github/workflows/security.yml"
CONTAINER_WORKFLOW_PATH = ROOT / ".github/workflows/container.yml"
DEPENDABOT_PATH = ROOT / ".github/dependabot.yml"
GITHUB_SECURITY_POLICY_PATH = ROOT / ".github/SECURITY.md"
LICENSE_PATH = ROOT / "LICENSE"
SECURITY_DOC_PATH = ROOT / "docs/security.md"


def test_security_workflow_runs_dependency_audit_and_trivy_scans() -> None:
    workflow = SECURITY_WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "name: Security" in workflow
    assert "pull_request:" in workflow
    assert "schedule:" in workflow
    assert "uv run --with pip-audit pip-audit --strict" in workflow
    assert 'TRIVY_VERSION: "0.70.0"' in workflow
    assert "trivy --version" in workflow
    assert "--scanners vuln,secret,misconfig" in workflow
    assert "docker/build-push-action@v6" in workflow
    assert "--format cyclonedx" in workflow
    assert "actions/upload-artifact@v4" in workflow
    assert "sbom-cyclonedx.json" in workflow
    assert "github/codeql-action/upload-sarif" not in workflow
    assert "aquasecurity/trivy-action" not in workflow


def test_security_workflow_scans_repository_and_container_image() -> None:
    workflow = SECURITY_WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "trivy fs" in workflow
    assert "trivy image" in workflow
    assert "--output trivy-repository.sarif" in workflow
    assert "name: trivy-repository-sarif" in workflow
    assert "--output trivy-image.sarif" in workflow
    assert "name: trivy-image-sarif" in workflow
    assert "--severity HIGH,CRITICAL" in workflow
    assert "--exit-code 0" in workflow


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
    assert "SARIF artifacts" in doc
    assert "Terraform placeholder Secrets" in doc


def test_repository_declares_license_and_security_policy() -> None:
    license_text = LICENSE_PATH.read_text(encoding="utf-8")
    security_policy = GITHUB_SECURITY_POLICY_PATH.read_text(encoding="utf-8")

    assert "MIT License" in license_text
    assert "Copyright (c) 2026 ictup" in license_text
    assert "Security Policy" in security_policy
    assert "Reporting a Vulnerability" in security_policy
