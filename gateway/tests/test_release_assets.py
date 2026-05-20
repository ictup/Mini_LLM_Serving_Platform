from pathlib import Path

import pytest

from scripts.check_release_version import (
    load_project_version,
    validate_release_tag,
    version_from_tag,
)

ROOT = Path(__file__).resolve().parents[2]
RELEASE_WORKFLOW_PATH = ROOT / ".github/workflows/release.yml"
CONTAINER_WORKFLOW_PATH = ROOT / ".github/workflows/container.yml"
RELEASE_DOC_PATH = ROOT / "docs/release_process.md"
CHANGELOG_PATH = ROOT / "CHANGELOG.md"
PYPROJECT_PATH = ROOT / "pyproject.toml"


def test_release_version_script_accepts_matching_project_tag() -> None:
    project_version = load_project_version(PYPROJECT_PATH)

    validate_release_tag(tag=f"v{project_version}", project_version=project_version)


def test_release_version_script_rejects_invalid_or_mismatched_tags() -> None:
    with pytest.raises(ValueError, match="vMAJOR.MINOR.PATCH"):
        version_from_tag("0.1.0")

    with pytest.raises(ValueError, match="does not match"):
        validate_release_tag(tag="v9.9.9", project_version="0.1.0")


def test_release_workflow_creates_github_release_for_semver_tags() -> None:
    workflow = RELEASE_WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "name: Release" in workflow
    assert '"v*.*.*"' in workflow
    assert "workflow_dispatch:" in workflow
    assert "contents: write" in workflow
    assert "python scripts/check_release_version.py --tag" in workflow
    assert "softprops/action-gh-release@v2" in workflow
    assert "generate_release_notes: true" in workflow
    assert "LLM Serving Gateway for vLLM" in workflow
    assert "Mini LLM Serving Platform" not in workflow


def test_container_workflow_publishes_versioned_image_tags() -> None:
    workflow = CONTAINER_WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "tags:" in workflow
    assert '"v*.*.*"' in workflow
    assert "type=ref,event=tag" in workflow
    assert "type=sha,prefix=sha-" in workflow
    assert "type=raw,value=main" in workflow
    assert "provenance: true" in workflow
    assert "sbom: true" in workflow


def test_release_docs_and_changelog_describe_release_contract() -> None:
    release_doc = RELEASE_DOC_PATH.read_text(encoding="utf-8")
    changelog = CHANGELOG_PATH.read_text(encoding="utf-8")
    project_version = load_project_version(PYPROJECT_PATH)

    assert "pyproject.toml is the source of truth" in release_doc
    assert "scripts/check_release_version.py --tag v0.1.1" in release_doc
    assert "git tag v0.1.1" in release_doc
    assert "GHCR" in release_doc
    assert "SBOM/provenance" in release_doc
    assert f"## {project_version} - 2026-05-20" in changelog
    assert "Portfolio benchmark and GPU observability release" in changelog
