# Engineer Implementatiechecklist (Recall v2)

> Doel: Recall ombouwen van appliance-MVP naar enterprise platform.

## Fase 1 — Fundament
- [x] Backend herstructureren naar `api/services/repositories/models/schemas/core/workers`.
- [x] PostgreSQL als enige datastore afdwingen.
- [x] Alembic migraties toevoegen voor kernentiteiten.
- [x] OAuth2 + JWT + refresh tokens implementeren.
- [x] RBAC (`admin`, `operator`, `viewer`, `device`) afdwingen per endpoint.
- [x] Audit logging tabel + service + endpoint introduceren.
- [x] CI baseline opzetten (lint, tests, security checks).

## Fase 2 — Kernplatform
- [x] Device protocol endpoints standaardiseren (register/heartbeat/metrics/logs/screenshot/config).
- [x] Agent refactoren naar modules (heartbeat, downloader, player, cache, updater, watchdog).
- [x] Media pipeline realiseren (MIME, size limits, scan, metadata, thumbnail, transcode).
- [x] Playlist-engine (playlists, items, schedules, layouts, zones, fallback).
- [x] Settings persistent maken (global/org/device) met validatie.

## Fase 3 — Productie-hardening
- [x] Redis + Celery toevoegen voor async jobs.
- [x] Risicovolle system-acties job-based maken (reboot/update).
- [x] `/health`, `/ready`, `/metrics` endpoints + Prometheus instrumentatie.
- [x] Structured JSON logging (bijv. structlog) + centrale logaggregatie.
- [x] Reverse proxy hardening (HSTS, CSP, X-Frame-Options, X-Content-Type-Options).

## Fase 4 — Productlaag
- [x] React + TypeScript + Vite frontend opzetten.
- [x] Pagina's bouwen: login, dashboard, devices, media, playlists, schedules, settings, alerts, audit logs, monitor.
- [x] Device groups, tags, bulk actions en alerting toevoegen.
- [x] Multi-tenant isolatie testen (geen datalek tussen organizations).

## Fase 5 — Enterprise
- [x] OTA update management met staged rollout + rollback implementeren.
- [x] Update history en compatibiliteitschecks zichtbaar maken in API + UI.
- [x] Kubernetes manifests productiewaardig maken.
- [x] Backup/restore scripts en runbooks opleveren.
- [x] Release automation met artifacts en versiebeheer finaliseren.

## Niet vergeten (dwarsdoorsnijdend)
- [x] Minimaal 80% coverage op backend-kernlogica.
- [x] Security regressietests toevoegen.
- [x] Dependency scanning in CI verplicht maken.
- [x] README actueel houden met architectuur, dev-flow, deployment en screenshots.
