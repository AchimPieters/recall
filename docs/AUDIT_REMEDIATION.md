# Audit remediation (architectuur, security, operations, maintainability, product)

Dit document koppelt de auditpunten aan concrete implementaties in deze repository.

## 1) Architectuur
- Gelaagde domeinstructuur aanwezig in `api/`, `services/`, `models/`, `db/`, `workers/`.
- Database laag met SQLAlchemy + migrations (`recall/db/database.py`, `recall/db/migrations/0001_init.sql`).
- Content pipeline uitgebreid met playlist- en schedule-services + API-routes.

## 2) Security
- OAuth2 password flow + JWT access tokens (`/token`).
- RBAC enforcement via `require_role` dependencies op routes.
- API rate limiting op login endpoint.
- Upload validatie (size/mime/filename) + optionele ClamAV malware scan.
- Security headers op elke request + audit logging op gevoelige system acties.

## 3) Operations
- Liveness/readiness/metrics endpoints (`/health`, `/ready`, `/metrics`).
- Prometheus metrics via `prometheus_client`.
- Structured request logging (`structlog`) en audit events.
- Device monitoring via heartbeat + status transitions (online/offline/unreachable).

## 4) Maintainability
- Pytest testsuite voor auth/health/security/settings en playlist scheduling.
- CI pipeline met linting, formatting, tests, security scan, docker build.
- Documentatie voor development, deployment, architecture en API.

## 5) Productvolwassenheid
- Playlist model + items + schedules in datamodel.
- Nieuwe playlist API voor CRUD-lite + item management + scheduling.
- Device config endpoint levert actieve playlist op basis van targeting (`device_id` of `all`).

## 6) Repository maturity
- `CHANGELOG.md`, `SECURITY.md`, `CONTRIBUTING.md` zijn aanwezig.
- GitHub Actions CI aanwezig.
- Deze remediatie is expliciet gedocumenteerd in dit bestand.
