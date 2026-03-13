# Disaster Recovery Runbook

## Doel
Dit document beschrijft de minimale enterprise DR-procedure voor Recall over database, media en herstelvalidatie.

## Scope
- API runtime (`backend/`)
- Worker runtime (`backend/app/workers`)
- Media storage (`media/` volume of object storage)
- Database (PostgreSQL in productie, SQLite alleen lokaal/test)

## RTO / RPO
- **RTO (Recovery Time Objective):** 4 uur
- **RPO (Recovery Point Objective):** 24 uur

## Backupbeleid

## 1) Database backups
- Frequentie: dagelijks (full backup)
- Tooling productie: `pg_dump -Fc`
- Bewaartermijn: minimaal 30 dagen
- Integriteitscheck: wekelijkse restore-validatie in staging

Voorbeeld:
```bash
pg_dump -Fc "$DATABASE_URL" > "backups/recall-$(date +%F).dump"
```

## 2) Media backups
- Frequentie: dagelijks snapshot of object-storage replication
- Scope: volledige `media/` inhoud
- Bewaartermijn: minimaal 30 dagen
- Integriteitscheck: checksum-sampling op willekeurige artifacts

Voorbeeld (filesystem volume):
```bash
rsync -a --delete media/ backups/media/$(date +%F)/
```

## 3) Backup metadata
- Registreer per backup minimaal:
  - timestamp
  - bronomgeving
  - artifactlocatie
  - checksum/hash
  - uitvoerder (job/service-account)

## Restore procedure

## 1) Database restore (PostgreSQL)
1. Maak doel-database leeg of herstel naar nieuwe target-db.
2. Voer restore uit:
   ```bash
   pg_restore --clean --if-exists -d "$TARGET_DATABASE_URL" < backup.dump
   ```
3. Draai schema-validatie + migratiecheck.
4. Start API/worker opnieuw en voer smoke-tests uit.

## 2) Media restore
1. Herstel media naar target volume/bucket.
2. Valideer directory- of objectstructuur.
3. Valideer checksums op steekproefset.

## 3) Applicatieherstelvalidatie
- API health/readiness:
  - `GET /api/v1/health`
  - `GET /api/v1/ready`
- Device protocol smoke:
  - `POST /api/v1/device/register`
  - `POST /api/v1/device/heartbeat`
- Kritieke business flows:
  - media list/upload
  - playlist resolve preview
  - alert listing

## Automatisering
- Plan backup jobs in scheduler/orchestrator (bijv. Kubernetes CronJob):
  - DB backup job: dagelijks
  - Media backup job: dagelijks
  - Restore drill job: maandelijks (staging)
- Gebruik als startpunt: `k8s/disaster-recovery-cronjobs.example.yaml` met voorbeeld-CronJobs voor DB backup, media backup en restore drill.
- Publiceer jobuitvoer en status als CI/CD artifact of logging event.

## Restore drills (verplicht)
- Frequentie: minimaal maandelijks in staging.
- Te registreren:
  - start/eindtijd
  - behaalde RTO/RPO
  - fouten en remediations
  - sign-off door operations owner

## Rollen en verantwoordelijkheden
- **Incident Commander:** coördineert herstelbesluit en statusupdates.
- **DB Owner:** voert database restore uit en valideert dataconsistentie.
- **Platform Owner:** herstelt runtimes, networking en secrets.
- **Product Owner:** voert functionele acceptatiechecks uit.

## Security tijdens DR
- Gebruik alleen geautoriseerde service-accounts.
- Restore geen backups naar niet-geautoriseerde omgevingen.
- Houd audit trail bij van alle backup/restore acties.

## Referenties
- `backend/app/db/backup_restore.py`
- `backend/tests/test_backup_restore.py`
- `docs/operations.md`
- `docs/deployment-environments.md`
- `k8s/disaster-recovery-cronjobs.example.yaml`
