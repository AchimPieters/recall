from tools.changelog_release_check import changelog_has_release


def test_changelog_has_release_accepts_matching_tag() -> None:
    text = """# Changelog\n\n## Unreleased\n- Item\n\n## v1.2.3 - 2026-03-11\n- Release notes\n"""
    assert changelog_has_release(text, "v1.2.3")
    assert changelog_has_release(text, "1.2.3")


def test_changelog_has_release_rejects_missing_or_mismatched_tag() -> None:
    text = """# Changelog\n\n## Unreleased\n- Item\n\n## v1.2.2 - 2026-03-10\n- Prior release\n"""
    assert not changelog_has_release(text, "v1.2.3")


def test_changelog_has_release_accepts_prerelease_heading() -> None:
    text = """# Changelog\n\n## v1.3.0-rc.1\n- Candidate\n"""
    assert changelog_has_release(text, "v1.3.0-rc.1")
