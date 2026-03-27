from pathlib import Path

from tools import release_artifact_scaffold as scaffold


def test_scaffold_release_artifacts_creates_expected_files(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    changed = scaffold.scaffold_release_artifacts("v3.0.0", "2026-03-13")

    assert "CHANGELOG.md" in changed
    assert "docs/releases/v3.0.0-enterprise.md" in changed
    assert "docs/releases/acceptance/v3.0.0-signoff.md" in changed

    changelog = (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## v3.0.0 - 2026-03-13" in changelog


def test_scaffold_release_artifacts_rejects_invalid_tag(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    try:
        scaffold.scaffold_release_artifacts("3.0.0", "2026-03-13")
    except ValueError as exc:
        assert "invalid release tag" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_scaffold_release_artifacts_no_overwrite_by_default(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    notes = tmp_path / "docs/releases/v3.1.0-enterprise.md"
    notes.parent.mkdir(parents=True, exist_ok=True)
    notes.write_text("original", encoding="utf-8")

    changed = scaffold.scaffold_release_artifacts("v3.1.0", "2026-03-13")

    assert "docs/releases/v3.1.0-enterprise.md" not in changed
    assert notes.read_text(encoding="utf-8") == "original"


def test_main_cli_success(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert scaffold.main(["v3.2.0", "--date", "2026-03-13"]) == 0
    assert (tmp_path / "docs/releases/v3.2.0-enterprise.md").exists()
