from __future__ import annotations

from pathlib import Path
import sys


DOCS_DIR = Path("docs")


def _first_non_empty_line(lines: list[str]) -> str | None:
    for line in lines:
        if line.strip():
            return line
    return None


def main() -> int:
    failures: list[str] = []
    for path in sorted(DOCS_DIR.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()

        first = _first_non_empty_line(lines)
        if first is None:
            failures.append(f"{path}: empty markdown file")
        elif not first.startswith("# "):
            failures.append(f"{path}: first non-empty line must be H1 heading")

        for idx, line in enumerate(lines, start=1):
            if line.rstrip(" \t") != line:
                failures.append(f"{path}:{idx}: trailing whitespace")

        if text and not text.endswith("\n"):
            failures.append(f"{path}: missing final newline")

    if failures:
        print("doc_lint failed:")
        for item in failures:
            print(f"- {item}")
        return 1

    print("doc_lint passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
