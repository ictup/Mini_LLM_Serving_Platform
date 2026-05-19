from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
README_PATH = ROOT / "README.md"
PORTFOLIO_PATH = ROOT / "docs/portfolio_summary.md"
REPOSITORY_METADATA_PATH = ROOT / "docs/repository_metadata.md"
PROJECT_STATUS_PATH = ROOT / "docs/project_status.md"


def test_readme_has_recruiter_snapshot_and_portfolio_signals() -> None:
    readme = README_PATH.read_text(encoding="utf-8")

    assert "## Recruiter Snapshot" in readme
    assert "AI platform engineering" in readme
    assert "Production operations" in readme
    assert "Performance discipline" in readme
    assert "Deployment maturity" in readme
    assert "Delivery hygiene" in readme
    assert "GitOps, Terraform, supply-chain checks, release automation" in readme


def test_portfolio_summary_has_updated_cv_and_interview_content() -> None:
    summary = PORTFOLIO_PATH.read_text(encoding="utf-8")

    assert "OpenAI-Compatible LLM Serving Platform with vLLM and Production Tooling" in summary
    assert "Argo CD, Terraform, GitHub Actions" in summary
    assert "model-aware TPM" in summary
    assert "p95/p99 latency" in summary
    assert "SBOM/provenance output" in summary
    assert "## Interview Talking Points" in summary
    assert "Why a Gateway is still useful" in summary
    assert "Why token-aware TPM matters" in summary


def test_repository_metadata_targets_current_project_scope() -> None:
    metadata = REPOSITORY_METADATA_PATH.read_text(encoding="utf-8")

    assert "llm-serving-gateway-vllm" in metadata
    assert "OpenAI-compatible LLM serving gateway with vLLM" in metadata
    assert "`argocd`" in metadata
    assert "`terraform`" in metadata
    assert "`gitops`" in metadata
    assert "`sbom`" in metadata
    assert "`supply-chain-security`" in metadata
    assert "gh repo edit --add-topic" in metadata


def test_project_status_tracks_repository_presentation() -> None:
    status = PROJECT_STATUS_PATH.read_text(encoding="utf-8")
    expected_row = (
        "| GitHub repository presentation guide | Done | `docs/repository_metadata.md` |"
    )

    assert expected_row in status
