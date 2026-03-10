import json
from pathlib import Path

import pytest

from backend.app.db.backup_restore import BackupRestoreError, backup_database, restore_database


def test_backup_database_creates_backup_and_manifest(tmp_path: Path) -> None:
    db_file = tmp_path / "recall.db"
    db_file.write_bytes(b"demo-db-bytes")

    result = backup_database(f"sqlite:///{db_file}", str(tmp_path / "backups"))

    backup_path = Path(result["backup_file"])
    manifest_path = Path(result["manifest_file"])

    assert backup_path.exists()
    assert backup_path.read_bytes() == b"demo-db-bytes"
    assert manifest_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["backup_file"] == str(backup_path)
    assert manifest["checksum_sha256"] == result["checksum_sha256"]


def test_restore_database_overwrites_sqlite_db(tmp_path: Path) -> None:
    db_file = tmp_path / "restore-target.db"
    db_file.write_bytes(b"old-bytes")

    backup_file = tmp_path / "backup-source.sqlite3"
    backup_file.write_bytes(b"new-bytes")

    result = restore_database(f"sqlite:///{db_file}", str(backup_file))

    assert db_file.read_bytes() == b"new-bytes"
    assert result["restored_file"] == str(db_file.resolve())


def test_backup_restore_rejects_non_sqlite_urls(tmp_path: Path) -> None:
    with pytest.raises(BackupRestoreError):
        backup_database("postgresql://recall:pass@localhost/recall", str(tmp_path))

    with pytest.raises(BackupRestoreError):
        restore_database("postgresql://recall:pass@localhost/recall", str(tmp_path / "b.sql"))
