# Engineer Implementatiechecklist (Recall v2)

> Doel: Recall ombouwen van appliance-MVP naar enterprise platform.

## Fase 1 — Fundament
- [ ] Backend herstructureren naar `api/services/repositories/models/schemas/core/workers`.
- [ ] PostgreSQL als enige datastore afdwingen.
- [ ] Alembic migraties toevoegen voor kernentiteiten.
- [ ] OAuth2 + JWT + refresh tokens implementeren.
- [ ] RBAC (`admin`, `operator`, `viewer`, `device`) afdwingen per endpoint.
- [ ] Audit logging tabel + service + endpoint introduceren.
- [ ] CI baseline opzetten (lint, tests, security checks).

## Fase 2 — Kernplatform
- [ ] Device protocol endpoints standaardiseren (register/heartbeat/metrics/logs/screenshot/config).
- [ ] Agent refactoren naar modules (heartbeat, downloader, player, cache, updater, watchdog).
- [ ] Media pipeline realiseren (MIME, size limits, scan, metadata, thumbnail, transcode).
- [ ] Playlist-engine (playlists, items, schedules, layouts, zones, fallback).
- [ ] Settings persistent maken (global/org/device) met validatie.

## Fase 3 — Productie-hardening
- [ ] Redis + Celery toevoegen voor async jobs.
- [ ] Risicovolle system-acties job-based maken (reboot/update).
- [ ] `/health`, `/ready`, `/metrics` endpoints + Prometheus instrumentatie.
- [ ] Structured JSON logging (bijv. structlog) + centrale logaggregatie.
- [ ] Reverse proxy hardening (HSTS, CSP, X-Frame-Options, X-Content-Type-Options).

## Fase 4 — Productlaag
- [ ] React + TypeScript + Vite frontend opzetten.
- [ ] Pagina's bouwen: login, dashboard, devices, media, playlists, schedules, settings, alerts, audit logs, monitor.
- [ ] Device groups, tags, bulk actions en alerting toevoegen.
- [ ] Multi-tenant isolatie testen (geen datalek tussen organizations).

## Fase 5 — Enterprise
- [ ] OTA update management met staged rollout + rollback implementeren.
- [ ] Update history en compatibiliteitschecks zichtbaar maken in API + UI.
- [ ] Kubernetes manifests productiewaardig maken.
- [ ] Backup/restore scripts en runbooks opleveren.
- [ ] Release automation met artifacts en versiebeheer finaliseren.

## Niet vergeten (dwarsdoorsnijdend)
- [ ] Minimaal 80% coverage op backend-kernlogica.
- [ ] Security regressietests toevoegen.
- [ ] Dependency scanning in CI verplicht maken.
- [ ] README actueel houden met architectuur, dev-flow, deployment en screenshots.
