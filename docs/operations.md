# Operations Runbook

## Backup and restore
- Database backups: run `pg_dump -Fc recall > backups/recall-$(date +%F).dump` daily.
- Media backups: snapshot `../media` volume daily.
- Restore drill: monthly restore into staging with `pg_restore -d recall_staging <dump>`.

## Rollout strategy
- Use blue/green or rolling deployment for API and worker.
- Health gate checks: `/live`, `/ready`, and `/metrics` must be green before traffic shift.

## Alerts and SLO baseline
- Alert on `/ready` failures, worker queue growth, and login failure spikes.
- Initial SLO target: 99.9% availability and p95 API latency < 300 ms.

## Incident handling
1. Declare severity and incident commander.
2. Freeze deploys and capture timeline in incident document.
3. Mitigate, validate with health/readiness/metrics checks, then close with postmortem.
