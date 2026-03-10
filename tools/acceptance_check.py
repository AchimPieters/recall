from __future__ import annotations

from pathlib import Path


SIGNOFF_DOC = Path("docs/runbooks/final-acceptance-signoff.md")
REQUIRED_HEADINGS = [
    "## Acceptance checklist",
    "## Evidence links (must be populated)",
    "## Sign-off record",
]


def main() -> int:
    if not SIGNOFF_DOC.exists():
        print(f"missing sign-off document: {SIGNOFF_DOC}")
        return 1

    text = SIGNOFF_DOC.read_text(encoding="utf-8")
    missing = [heading for heading in REQUIRED_HEADINGS if heading not in text]
    if missing:
        print("sign-off document missing required sections:")
        for heading in missing:
            print(f"- {heading}")
        return 1

    print("acceptance_check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
