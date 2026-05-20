import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEMO_SCRIPT_PATH = ROOT / "scripts/demo_portfolio.py"
MAKEFILE_PATH = ROOT / "Makefile"
README_PATH = ROOT / "README.md"


def test_demo_script_prints_portfolio_walkthrough() -> None:
    result = subprocess.run(
        [sys.executable, str(DEMO_SCRIPT_PATH), "--profile", "all"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "OpenAI-Compatible LLM Serving Gateway" in result.stdout
    assert "FastAPI Gateway" in result.stdout
    assert "vLLM" in result.stdout
    assert "Prometheus" in result.stdout
    assert "Terraform" in result.stdout


def test_demo_entrypoints_are_documented() -> None:
    makefile = MAKEFILE_PATH.read_text(encoding="utf-8")
    readme = README_PATH.read_text(encoding="utf-8")

    assert "demo:" in makefile
    assert "demo-local:" in makefile
    assert "uv run python scripts/demo_portfolio.py" in readme
    assert "docs/demo.md" in readme
