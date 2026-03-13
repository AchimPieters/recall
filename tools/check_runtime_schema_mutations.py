#!/usr/bin/env python3
"""Fail when runtime code contains schema mutation patterns.

This policy intentionally ignores migration folders because schema mutations
must live there.
"""

from __future__ import annotations

import argparse
from pathlib import Path

BANNED_TOKENS = (
    "Base.metadata.create_all(",
    "ALTER TABLE",
)

# Paths are repo-relative
EXCLUDED_PARTS = {
    "backend/app/db/migrations",
    "backend/alembic/versions",
    "backend/tests",
}


def _is_excluded(path: Path, repo_root: Path) -> bool:
    rel = path.relative_to(repo_root).as_posix()
    return any(rel.startswith(prefix) for prefix in EXCLUDED_PARTS)


def find_violations(repo_root: Path) -> list[str]:
    violations: list[str] = []
    scan_roots = [repo_root / "backend" / "app", repo_root / "agent"]

    for scan_root in scan_roots:
        if not scan_root.exists():
            continue
        for path in sorted(scan_root.rglob("*.py")):
            if _is_excluded(path, repo_root):
                continue
            content = path.read_text(encoding="utf-8")
            for token in BANNED_TOKENS:
                if token in content:
                    rel = path.relative_to(repo_root).as_posix()
                    violations.append(f"{rel}: contains '{token}'")
    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Path to repository root (default: current directory)",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    violations = find_violations(repo_root)
    if violations:
        print("Runtime schema mutation policy violations found:")
        for violation in violations:
            print(f"- {violation}")
        return 1

    print("Runtime schema mutation policy check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
