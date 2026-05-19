# Security and Supply Chain

This project includes lightweight supply-chain controls that are practical for a
portfolio repository and easy to extend in a production organization.

## Automated Checks

| Workflow | Purpose |
| --- | --- |
| `.github/workflows/security.yml` | Dependency audit, repository/IaC scan, container image scan, and SBOM artifact. |
| `.github/workflows/container.yml` | Publishes the Gateway image with Docker Buildx provenance and SBOM attestations. |
| `.github/dependabot.yml` | Opens scheduled update PRs for GitHub Actions, Python dependencies, and Docker base images. |

## Security Workflow

The security workflow runs on pushes, pull requests, a weekly schedule, and
manual dispatch.

It performs three jobs:

- `dependency-audit`: installs the locked project environment and runs
  `pip-audit`.
- `repository-scan`: runs Trivy against the repository for dependency,
  secret, and IaC misconfiguration findings, uploads the SARIF file as an
  artifact, then attempts a best-effort upload to GitHub code scanning.
- `image-scan`: builds the local Gateway image, scans it with Trivy, uploads
  the SARIF file as an artifact, attempts a best-effort upload to GitHub code
  scanning, and publishes a CycloneDX SBOM artifact.

Trivy scans are configured as report-first checks because container base-image
CVEs can change independently of project code. The intended production path is
to review code-scanning alerts, pin patched base images, and tighten exit-code
gates once a team has an agreed vulnerability SLA.

SARIF artifacts are the durable evidence for portfolio and release review.
GitHub code-scanning uploads are allowed to fail without failing the whole
workflow because repository visibility, permissions, and code-scanning
availability can differ across forks and personal accounts.

## Local Equivalents

Dependency audit:

```bash
uv sync --frozen --all-groups
uv run --with pip-audit pip-audit --strict
```

Build and scan image:

```bash
docker build -f Dockerfile.gateway -t mini-llm-serving-platform:security-scan .
trivy image --severity HIGH,CRITICAL mini-llm-serving-platform:security-scan
trivy image --format cyclonedx --output sbom-cyclonedx.json mini-llm-serving-platform:security-scan
```

Repository and IaC scan:

```bash
trivy fs --scanners vuln,secret,misconfig --severity HIGH,CRITICAL .
```

## Production Notes

- Treat SARIF artifacts and code-scanning findings as triage input, not as a
  replacement for dependency
  ownership.
- Pin release images by immutable tags or digests before production rollout.
- Keep generated SBOMs with release artifacts.
- Do not commit real API keys, Hugging Face tokens, kubeconfigs, or Terraform
  state files.
- If Terraform placeholder Secrets are enabled for a lab cluster, protect the
  state backend as sensitive data.
