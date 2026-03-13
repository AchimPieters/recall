from __future__ import annotations

import re
import sys
from pathlib import Path


TAG_PATTERN = re.compile(r"^v\d+\.\d+\.\d+(?:-(?:alpha|beta|rc\.\d+))?$")


def validate_release_tag(tag: str) -> bool:
    return bool(TAG_PATTERN.fullmatch(tag.strip()))


def expected_release_notes_path(tag: str) -> Path:
    return Path("docs/releases") / f"{tag.strip()}-enterprise.md"


def expected_signoff_path(tag: str) -> Path:
    return Path("docs/releases/acceptance") / f"{tag.strip()}-signoff.md"


def validate_release_artifacts(tag: str) -> list[str]:
    errors: list[str] = []
    notes_path = expected_release_notes_path(tag)
    signoff_path = expected_signoff_path(tag)
    if not notes_path.exists():
        errors.append(f"missing release notes: {notes_path}")
    if not signoff_path.exists():
        errors.append(f"missing release sign-off: {signoff_path}")
    return errors


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print("usage: python tools/release_gate_check.py <tag>")
        return 2

    tag = args[0]
    if not validate_release_tag(tag):
        print(f"invalid release tag: {tag}")
        return 1

    artifact_errors = validate_release_artifacts(tag)
    if artifact_errors:
        print("release gate check failed:")
        for err in artifact_errors:
            print(f"- {err}")
        return 1

    print(f"release gate check passed for tag {tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
