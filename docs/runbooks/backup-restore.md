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
