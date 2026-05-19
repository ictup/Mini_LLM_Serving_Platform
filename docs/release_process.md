# Release Process

This project uses explicit SemVer tags and a small release verification script
so published source releases, Python metadata, and GHCR image tags stay aligned.

## Version Rules

pyproject.toml is the source of truth for release versioning.

- `pyproject.toml` is the source of truth for the project version.
- Release tags must use `vMAJOR.MINOR.PATCH`.
- The tag version must match `pyproject.toml`.
- Container images are published by `.github/workflows/container.yml` with
  `main`, `sha-*`, and tag-based image tags.
- GitHub Releases are created by `.github/workflows/release.yml`.

## Pre-Release Checklist

Run the local quality gate:

```bash
uv sync --frozen --all-groups
uv run ruff check .
uv run pytest
helm lint deploy/helm
helm template mini-llm deploy/helm --namespace mini-llm-serving
helm template mini-llm deploy/helm \
  --namespace mini-llm-serving \
  --set vllm.enabled=true \
  --set mockBackend.enabled=false
```

Validate the intended tag:

```bash
uv run python scripts/check_release_version.py --tag v0.1.1
```

## Create a Release

Update `pyproject.toml` and `CHANGELOG.md`, then create and push the tag:

```bash
git tag v0.1.1
git push origin v0.1.1
```

Pushing the tag starts two workflows:

- `Container image`: publishes the GHCR image and Buildx SBOM/provenance
  attestations.
- `Release`: verifies the tag/version match and creates a GitHub Release with
  generated release notes.

## Verify Release Artifacts

After the workflows complete:

- Confirm the GitHub Release exists for the tag.
- Confirm GHCR has the same `vMAJOR.MINOR.PATCH` image tag.
- Confirm the security workflow or release review has SBOM and scan evidence.
- Use immutable version tags or digests in production GitOps values.

## Rollback

For a GitOps-managed environment, rollback by changing the image tag in the
Argo CD/Helm values to the previous known-good release tag and letting Argo CD
sync the desired state.
