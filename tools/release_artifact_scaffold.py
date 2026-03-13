from __future__ import annotations

from datetime import date
from pathlib import Path
import sys

try:
    from tools.release_gate_check import validate_release_tag
except ModuleNotFoundError:  # pragma: no cover - direct script invocation
    from release_gate_check import validate_release_tag


CHANGELOG_PATH = Path("CHANGELOG.md")
RELEASES_DIR = Path("docs/releases")
ACCEPTANCE_DIR = RELEASES_DIR / "acceptance"


def _parse_args(argv: list[str] | None = None) -> tuple[str, str, bool]:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args:
        raise ValueError("missing required <tag>")

    tag = args[0].strip()
    release_date = date.today().isoformat()
    overwrite = False

    i = 1
    while i < len(args):
        arg = args[i]
        if arg == "--date":
            if i + 1 >= len(args):
                raise ValueError("--date requires YYYY-MM-DD")
            release_date = args[i + 1].strip()
            i += 2
            continue
        if arg == "--overwrite":
            overwrite = True
            i += 1
            continue
        raise ValueError(f"unknown argument: {arg}")

    return tag, release_date, overwrite


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _write_file(path: Path, content: str, overwrite: bool) -> bool:
    if path.exists() and not overwrite:
        return False
    _ensure_parent(path)
    path.write_text(content, encoding="utf-8")
    return True


def _ensure_changelog_heading(tag: str, release_date: str, overwrite: bool) -> bool:
    if not CHANGELOG_PATH.exists():
        base = "# Changelog\n\n## Unreleased\n\n"
        CHANGELOG_PATH.write_text(base, encoding="utf-8")

    text = CHANGELOG_PATH.read_text(encoding="utf-8")
    heading = f"## {tag} - {release_date}"
    if heading in text and not overwrite:
        return False

    marker = "## Unreleased\n"
    insert = (
        f"{marker}\n"
        f"{heading}\n"
        "- Summarize the release changes here.\n"
        "- Link evidence and notable operational/security impacts.\n\n"
    )

    if marker in text:
        updated = text.replace(marker, insert, 1)
    else:
        updated = f"# Changelog\n\n## Unreleased\n\n{heading}\n- Summarize the release changes here.\n\n{text}"

    CHANGELOG_PATH.write_text(updated, encoding="utf-8")
    return True


def _release_notes_content(tag: str, release_date: str) -> str:
    return f"""# Recall Enterprise {tag} Release Notes

Release date: {release_date}

## Highlights
- Describe key product, platform, and security outcomes.

## Operational impact
- Describe SRE/operations impact and mitigations.

## Backward compatibility
- Document API/device compatibility expectations.
"""


def _signoff_content(tag: str, release_date: str) -> str:
    return f"""# Final Acceptance Sign-off ({tag})

## Acceptance checklist
- [ ] Security hardening checklist completed and approved.
- [ ] Load/performance baseline report approved (target profile + pass criteria).
- [ ] Failover drill executed and recovery objectives met.
- [ ] Disaster recovery restore drill executed in isolated environment.
- [ ] CI required checks and release gates configured and enforced.
- [ ] Final go/no-go meeting completed with explicit sign-off.

## Evidence links (must be populated)
- Security report: docs/security.md
- Load test report: docs/runbooks/onboarding-dry-run.md
- Failover drill report: docs/operations.md
- Disaster recovery report: docs/disaster-recovery.md
- Release gate screenshot/config export: .github/workflows/release.yml

## Sign-off record
- Version: {tag}
- Date: {release_date}
- Security lead approval: TBD
- Platform lead approval: TBD
- Product owner approval: TBD
"""


def scaffold_release_artifacts(tag: str, release_date: str, overwrite: bool = False) -> list[str]:
    if not validate_release_tag(tag):
        raise ValueError(f"invalid release tag: {tag}")

    created: list[str] = []
    notes_path = RELEASES_DIR / f"{tag}-enterprise.md"
    signoff_path = ACCEPTANCE_DIR / f"{tag}-signoff.md"

    if _write_file(notes_path, _release_notes_content(tag, release_date), overwrite):
        created.append(str(notes_path))
    if _write_file(signoff_path, _signoff_content(tag, release_date), overwrite):
        created.append(str(signoff_path))
    if _ensure_changelog_heading(tag, release_date, overwrite):
        created.append(str(CHANGELOG_PATH))

    return created


def main(argv: list[str] | None = None) -> int:
    try:
        tag, release_date, overwrite = _parse_args(argv)
    except ValueError as exc:
        print(f"argument error: {exc}")
        print(
            "usage: python tools/release_artifact_scaffold.py <tag> "
            "[--date YYYY-MM-DD] [--overwrite]"
        )
        return 2

    try:
        created = scaffold_release_artifacts(tag, release_date, overwrite=overwrite)
    except ValueError as exc:
        print(str(exc))
        return 1

    if not created:
        print(f"no files changed for {tag}")
        return 0

    print(f"scaffolded release artifacts for {tag}:")
    for item in created:
        print(f"- {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
