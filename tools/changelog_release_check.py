from __future__ import annotations

from pathlib import Path
import re
import sys


RELEASE_HEADING_PATTERN = re.compile(r"^##\s+v(?P<version>\d+\.\d+\.\d+(?:-(?:alpha|beta|rc\.\d+))?)\b", re.IGNORECASE)


def changelog_has_release(changelog_text: str, tag: str) -> bool:
    normalized_tag = tag.strip().lower()
    if normalized_tag.startswith("v"):
        normalized_tag = normalized_tag[1:]

    for raw_line in changelog_text.splitlines():
        line = raw_line.strip()
        match = RELEASE_HEADING_PATTERN.match(line)
        if match and match.group("version").lower() == normalized_tag:
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print("usage: python tools/changelog_release_check.py <tag>")
        return 2

    tag = args[0].strip()
    changelog_path = Path("CHANGELOG.md")
    if not changelog_path.exists():
        print("CHANGELOG.md not found")
        return 1

    if not changelog_has_release(changelog_path.read_text(encoding="utf-8"), tag):
        print(f"missing changelog section for release tag {tag}")
        return 1

    print(f"changelog gate check passed for tag {tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
