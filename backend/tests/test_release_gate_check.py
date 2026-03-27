from pathlib import Path

from tools.release_gate_check import (
    expected_release_notes_path,
    expected_signoff_path,
    validate_release_artifacts,
    validate_release_tag,
)


def test_validate_release_tag_accepts_stable_and_prerelease() -> None:
    assert validate_release_tag("v1.2.3")
    assert validate_release_tag("v1.2.3-alpha")
    assert validate_release_tag("v1.2.3-beta")
    assert validate_release_tag("v1.2.3-rc.1")


def test_validate_release_tag_rejects_invalid_patterns() -> None:
    assert not validate_release_tag("1.2.3")
    assert not validate_release_tag("v1.2")
    assert not validate_release_tag("v1.2.3-rc")
    assert not validate_release_tag("v1.2.3-preview")


def test_release_paths_match_expected_convention() -> None:
    assert expected_release_notes_path("v1.2.3") == Path(
        "docs/releases/v1.2.3-enterprise.md"
    )
    assert expected_signoff_path("v1.2.3") == Path(
        "docs/releases/acceptance/v1.2.3-signoff.md"
    )


def test_validate_release_artifacts_requires_notes_and_signoff(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "docs/releases/acceptance").mkdir(parents=True, exist_ok=True)

    errors = validate_release_artifacts("v1.2.3")
    assert "missing release notes: docs/releases/v1.2.3-enterprise.md" in errors
    assert (
        "missing release sign-off: docs/releases/acceptance/v1.2.3-signoff.md" in errors
    )


def test_validate_release_artifacts_passes_when_files_exist(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    notes = tmp_path / "docs/releases/v1.2.3-enterprise.md"
    signoff = tmp_path / "docs/releases/acceptance/v1.2.3-signoff.md"
    notes.parent.mkdir(parents=True, exist_ok=True)
    signoff.parent.mkdir(parents=True, exist_ok=True)
    notes.write_text("# notes\n", encoding="utf-8")
    signoff.write_text("# signoff\n", encoding="utf-8")

    assert validate_release_artifacts("v1.2.3") == []
