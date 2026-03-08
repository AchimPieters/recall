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

## Dashboards and tracing
- Maintain a primary dashboard with: request rate, p95/p99 latency,
  error rate, queue depth, online/offline device counts, and login failure rate.
- Propagate `X-Request-ID` through reverse proxy and API logs for incident correlation.
- Export traces to an OpenTelemetry backend in staging and production before cutover.

## Secrets and rotation
- Use `JWT_SECRETS` for key rotation with newest secret first and previous secret(s)
  retained during rollout overlap.
- Store runtime secrets in environment-injected secret stores (Vault/KMS/secret manager),
  never committed files.

## Incident handling
1. Declare severity and incident commander.
2. Freeze deploys and capture timeline in incident document.
3. Mitigate, validate with health/readiness/metrics checks, then close with postmortem.
