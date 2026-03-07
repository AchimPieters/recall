# Audit remediation (architectuur, security, operations, maintainability, product)

Dit document koppelt elk auditpunt aan concrete implementaties in deze repository.

## 1) Architectuur audit
- Domeinstructuur aanwezig en gebruikt: `api`, `services`, `repositories`, `models`, `db`, `workers`, `events`.
- Datalaag aanwezig: SQLAlchemy models + session management + SQL bootstrap migration (`0001_init.sql`).
- PostgreSQL is standaard in `docker-compose` met `psycopg2` driver.
- Content pipeline uitgebreid met playlist scheduling, layouts en device-targeting.

## 2) Security audit
- OAuth2 + JWT access tokens (`/token`) met role checking uit database (voorkomt stale claims).
- RBAC op routes via `require_role(...)` dependencies.
- Login rate limiting actief.
- Upload hardening: max size, MIME allowlist, filename sanitation, blocked executable extensions.
- Malware scan hook via ClamAV INSTREAM.
- Security headers + request-id op elke response.
- Settings mutaties zijn nu schema-gedreven (Pydantic allowlist; geen vrije dict-mutatie).
- `SECURITY.md` + responsible disclosure policy aanwezig.

## 3) Operations audit
- Endpoints voor health/liveness/readiness/metrics: `/health`, `/live`, `/ready`, `/metrics`.
- Prometheus gauges + request latency histogram.
- Structured logging met request-id voor correlatie.
- Device monitoring (heartbeat/status transitions), plus alerts API.
- Redis + Celery worker pad toegevoegd voor background jobs.
- Event stream (`/events`) voor operationele/audit traceability.

## 4) Maintainability audit
- Testsuite uitgebreid met auth/health/playlists/platform maturity en events/settings-validatie.
- CI pipeline bevat ruff, black, mypy, bandit, pytest, dependency audit en docker build.
- Repo bevat development/deployment/architecture/API documentatie.

## 5) Productvolwassenheid audit
- Playlist engine: playlists + items + scheduling windows.
- Device groups: create/list/assign API.
- Alerts: create/list/resolve API.
- Layouts: create/list API.
- Remote screenshots: device screenshot ingest + listing API.
- Multi-tenant fundament in datamodel (`organization_id` op users/devices/media).

## 6) Repository maturity
- Volwassen OSS signalen aanwezig: `CHANGELOG.md`, `SECURITY.md`, `CONTRIBUTING.md`, CI workflow.
- Remediatie expliciet vastgelegd in dit document.

## 7) Realistische score update
- Architectuur: verbeterd door expliciete repository + events laag.
- Security: verbeterd door hardening en schema-validatie op settings mutaties.
- Operations: verbeterd met liveness + latency metrics + events + worker infrastructuur.
- Maintainability: verbeterd met extra tests en CI quality/security checks.
- Productvolwassenheid: verbeterd met groups/layouts/alerts/screenshots/scheduling.

## 8) Waarom dit positief is
- Kleine codebase blijft snel refactorbaar.
- Toegevoegde componenten zijn modulair gehouden i.p.v. premature microservices.

## 9) Pad naar 10/10
- Volgende stap blijft: CI/CD release automation, deeper observability (tracing backend), OTA rollbacks,
  policy-as-code security controls en volwaardige front-end workflows.
