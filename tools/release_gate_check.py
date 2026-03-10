from __future__ import annotations

import re
import sys


TAG_PATTERN = re.compile(r"^v\d+\.\d+\.\d+(?:-(?:alpha|beta|rc\.\d+))?$")


def validate_release_tag(tag: str) -> bool:
    return bool(TAG_PATTERN.fullmatch(tag.strip()))


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print("usage: python tools/release_gate_check.py <tag>")
        return 2

    tag = args[0]
    if not validate_release_tag(tag):
        print(f"invalid release tag: {tag}")
        return 1

    print(f"release gate check passed for tag {tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
