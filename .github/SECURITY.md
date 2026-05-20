# Security Policy

## Supported Versions

Security fixes are maintained for the default branch and the latest tagged
release.

| Version | Supported |
| --- | --- |
| `main` | Yes |
| Latest release | Yes |
| Older releases | Best effort |

## Reporting a Vulnerability

If you find a vulnerability, do not publish exploit details in a public issue.
Use GitHub private vulnerability reporting when it is available for this
repository. If private reporting is not available, open a minimal public issue
that describes the affected area without secrets, exploit payloads, or sensitive
environment details.

Please include:

- Affected component or workflow.
- Impact and expected risk.
- Reproduction steps with sensitive values removed.
- Suggested fix, if known.

## Security Scope

This repository includes example deployment assets, local development secrets,
and portfolio infrastructure code. Placeholder API keys, local Docker Compose
settings, and example Kubernetes or Terraform secrets are not production
credentials and must be replaced before shared or public deployment.
