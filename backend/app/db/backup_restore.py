from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil


class BackupRestoreError(RuntimeError):
    pass


def _resolve_sqlite_path(database_url: str) -> Path:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise BackupRestoreError("only sqlite URLs are currently supported")
    raw_path = database_url[len(prefix) :]
    return Path(raw_path).resolve()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def backup_database(database_url: str, backup_dir: str) -> dict[str, str]:
    db_path = _resolve_sqlite_path(database_url)
    if not db_path.exists():
        raise BackupRestoreError(f"database file not found: {db_path}")

    target_dir = Path(backup_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_file = target_dir / f"recall-db-{stamp}.sqlite3"
    shutil.copy2(db_path, backup_file)

    checksum = _sha256_file(backup_file)
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "database_url": database_url,
        "backup_file": str(backup_file),
        "checksum_sha256": checksum,
    }
    manifest_path = target_dir / f"recall-db-{stamp}.manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {
        "backup_file": str(backup_file),
        "manifest_file": str(manifest_path),
        "checksum_sha256": checksum,
    }


def restore_database(database_url: str, backup_file: str) -> dict[str, str]:
    db_path = _resolve_sqlite_path(database_url)
    source = Path(backup_file).resolve()
    if not source.exists():
        raise BackupRestoreError(f"backup file not found: {source}")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, db_path)

    return {
        "restored_file": str(db_path),
        "checksum_sha256": _sha256_file(db_path),
    }
