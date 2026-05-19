from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path

SEMVER_TAG_PATTERN = re.compile(r"^v(?P<version>\d+\.\d+\.\d+)$")


def load_project_version(pyproject_path: Path) -> str:
    payload = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    return str(payload["project"]["version"])


def version_from_tag(tag: str) -> str:
    match = SEMVER_TAG_PATTERN.fullmatch(tag)
    if not match:
        raise ValueError(f"release tag must use vMAJOR.MINOR.PATCH format, got {tag!r}")
    return match.group("version")


def validate_release_tag(*, tag: str, project_version: str) -> None:
    tag_version = version_from_tag(tag)
    if tag_version != project_version:
        raise ValueError(
            f"release tag {tag!r} does not match pyproject.toml version {project_version!r}"
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate that a release tag matches pyproject.toml version."
    )
    parser.add_argument("--tag", required=True, help="Release tag, for example v0.1.0.")
    parser.add_argument(
        "--pyproject",
        default="pyproject.toml",
        type=Path,
        help="Path to pyproject.toml.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    project_version = load_project_version(args.pyproject)
    try:
        validate_release_tag(tag=args.tag, project_version=project_version)
    except ValueError as exc:
        print(f"release version check failed: {exc}", file=sys.stderr)
        return 1

    print(f"release version check passed: {args.tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
