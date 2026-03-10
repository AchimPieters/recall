# Runbook: Backup & Restore

## Backup
- Export PostgreSQL logical backup.
- Snapshot media storage.
- Save configuration and secrets metadata.

## Restore
- Restore database into isolated environment first.
- Validate schema migration state.
- Restore media and reindex metadata.
- Perform smoke tests before production cutover.


## Local SQLite drill (automation baseline)
1. Create a backup manifest + DB copy via Python helper:
   `python -c "from backend.app.db.backup_restore import backup_database; print(backup_database('sqlite:///./recall.db', './backups'))"`
2. Restore from a chosen copy:
   `python -c "from backend.app.db.backup_restore import restore_database; print(restore_database('sqlite:///./recall.db', './backups/<file>.sqlite3'))"`
3. Validate API health/readiness and sample queries after restore.
