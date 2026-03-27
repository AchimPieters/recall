from pathlib import Path

from tools import acceptance_check


def test_acceptance_signoff_document_has_required_sections() -> None:
    assert acceptance_check.main([]) == 0


def test_acceptance_check_strict_passes_for_completed_signoff(tmp_path: Path) -> None:
    signoff = tmp_path / "signoff.md"
    signoff.write_text(
        """# Signoff

## Acceptance checklist
- [x] Item A

## Evidence links (must be populated)
- Report: docs/report.md

## Sign-off record
- Version: v1.0.0
- Date: 2026-03-13
- Security lead approval: jane.doe
- Platform lead approval: john.ops
- Product owner approval: alex.product
""",
        encoding="utf-8",
    )

    assert acceptance_check.main(["--strict", "--file", str(signoff)]) == 0


def test_acceptance_check_strict_fails_for_unchecked_or_incomplete_fields(
    tmp_path: Path,
) -> None:
    signoff = tmp_path / "bad-signoff.md"
    signoff.write_text(
        """# Signoff

## Acceptance checklist
- [ ] Item A

## Evidence links (must be populated)
- Report: docs/report.md

## Sign-off record
- Version: v1.0.0
- Date: 2026-03-13
- Security lead approval: TBD
- Platform lead approval: approved
- Product owner approval: approved
""",
        encoding="utf-8",
    )

    assert acceptance_check.main(["--strict", "--file", str(signoff)]) == 1


def test_acceptance_check_strict_enforces_expected_version(tmp_path: Path) -> None:
    signoff = tmp_path / "version-signoff.md"
    signoff.write_text(
        """# Signoff

## Acceptance checklist
- [x] Item A

## Evidence links (must be populated)
- Report: docs/report.md

## Sign-off record
- Version: v1.2.3
- Date: 2026-03-13
- Security lead approval: sec.lead
- Platform lead approval: platform.lead
- Product owner approval: product.owner
""",
        encoding="utf-8",
    )

    assert (
        acceptance_check.main(
            ["--strict", "--file", str(signoff), "--expected-version", "v1.2.4"]
        )
        == 1
    )


def test_acceptance_check_strict_rejects_placeholder_approvals_and_bad_date(
    tmp_path: Path,
) -> None:
    signoff = tmp_path / "identity-signoff.md"
    signoff.write_text(
        """# Signoff

## Acceptance checklist
- [x] Item A

## Evidence links (must be populated)
- Report: docs/report.md

## Sign-off record
- Version: v1.2.3
- Date: 13-03-2026
- Security lead approval: approved-by-security-lead
- Platform lead approval: platform.lead
- Product owner approval: approved-by-product-owner
""",
        encoding="utf-8",
    )

    assert acceptance_check.main(["--strict", "--file", str(signoff)]) == 1
