from pathlib import Path


def test_disaster_recovery_runbook_and_cronjobs_cover_backup_and_restore() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    runbook = (repo_root / "docs" / "disaster-recovery.md").read_text(encoding="utf-8")
    cronjobs = (
        repo_root / "k8s" / "disaster-recovery-cronjobs.example.yaml"
    ).read_text(encoding="utf-8")

    runbook_required = [
        "Database backups",
        "Media backups",
        "Restore drills (verplicht)",
        "DB backup job: dagelijks",
        "Media backup job: dagelijks",
        "Restore drill job: maandelijks (staging)",
        "GET /api/v1/health",
        "GET /api/v1/ready",
    ]
    cronjob_required = [
        "name: recall-db-backup",
        "name: recall-media-backup",
        "name: recall-dr-restore-drill",
        "namespace: recall-staging",
        "pg_dump -Fc",
        "pg_restore --clean --if-exists",
        "rsync -a --delete",
    ]

    missing_runbook = [token for token in runbook_required if token not in runbook]
    missing_cron = [token for token in cronjob_required if token not in cronjobs]

    assert not missing_runbook, "DR runbook missing required sections: " + ", ".join(
        missing_runbook
    )
    assert not missing_cron, "DR cronjobs spec missing required controls: " + ", ".join(
        missing_cron
    )
