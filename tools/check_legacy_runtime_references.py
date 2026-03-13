#!/usr/bin/env python3
"""Fail if runtime/CI code still references the removed legacy runtime."""

from __future__ import annotations

import argparse
from pathlib import Path

DISALLOWED_TOKEN = "recall" + "-server"

# Historical docs and uninstall cleanup are allowed to reference legacy units.
EXCLUDED_DIRS = {
    "docs",
    "frontend/node_modules",
    ".git",
    "__pycache__",
    ".venv",
}

EXCLUDED_FILES = {
    "uninstall.sh",
}

TARGET_EXTENSIONS = {
    ".py",
    ".sh",
    ".yml",
    ".yaml",
    ".toml",
    ".ini",
    ".md",
}

TARGET_BASENAMES = {
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
}


def _should_scan(path: Path) -> bool:
    if any(part in EXCLUDED_DIRS for part in path.parts):
        return False
    if path.name in EXCLUDED_FILES:
        return False
    if path.name in TARGET_BASENAMES:
        return True
    return path.suffix in TARGET_EXTENSIONS


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    violations: list[str] = []

    for path in sorted(root.rglob("*")):
        if not path.is_file() or not _should_scan(path):
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if DISALLOWED_TOKEN in content:
            violations.append(str(path.relative_to(root)))

    if violations:
        print("Legacy runtime references detected:")
        for v in violations:
            print(f" - {v}")
        return 1

    print("OK: no legacy runtime references found in runtime/CI code paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
