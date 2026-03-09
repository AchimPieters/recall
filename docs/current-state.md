# Current State Baseline (Frozen)

_Last updated: 2026-03-08_

## Scope and freeze intent
This document freezes the current implementation baseline before enterprise rebuild work proceeds. The current platform already contains a partially modularized backend (`recall-server/recall`), a React frontend (`frontend/src`), and a modularized agent (`recall-player/agent_modules`).

## Repository inventory

### Backend endpoints (FastAPI)
Mounted with and without `/api/v1` prefix.

- Device protocol and fleet endpoints
  - `POST /device/register`
  - `POST /device/heartbeat`
  - `GET /device/config`
  - `POST /device/logs`
  - `GET /device/logs`
  - `POST /device/screenshot`
  - `GET /device/screenshots`
  - `POST /device/metrics`
  - `GET /device/list`
  - `POST /device/groups`
  - `GET /device/groups`
  - `POST /device/groups/{group_id}/members`
  - `POST /device/groups/{group_id}/bulk`
- Media
  - `POST /media/upload`
  - `GET /media`
- Playlists and layouts
  - `POST /playlists`
  - `GET /playlists`
  - `POST /playlists/{playlist_id}/items`
  - `GET /playlists/{playlist_id}/items`
  - `POST /playlists/{playlist_id}/schedule`
  - `POST /playlists/layouts`
  - `GET /playlists/layouts`
- Settings
  - `GET /settings`
  - `POST /settings`
  - `POST /settings/apply`
- Monitoring and alerts
  - `GET /monitor`
  - `POST /monitor/alerts`
  - `GET /monitor/alerts`
  - `POST /monitor/alerts/{alert_id}/resolve`
- Security and audit
  - `GET /security/audit`
- Events and system
  - `GET /events`
  - `POST /system/reboot`
  - `POST /system/update`
- Platform and observability
  - `GET /`
  - `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`
  - `GET /health`, `GET /ready`, `GET /metrics`

### Agent functionality (current)
The player agent is split into modules and currently supports:
- auth/runtime configuration validation
- device registration + heartbeat/config polling
- OTA version reporting
- media download
- local config caching
- offline playback from cached file
- retry/backoff watchdog loop

### Web pages / UI
Two UI layers currently exist:
- Legacy static pages in `recall-server/web/` (`index.html`, `devices.html`, `media.html`, `monitor.html`, `settings.html`)
- React + TypeScript frontend in `frontend/src/pages/` with pages:
  - Dashboard
  - Devices
  - Media
  - Playlists
  - Schedules
  - Alerts
  - Audit Logs
  - Settings

### Docker / deployment setup
- Docker assets:
  - `docker/Dockerfile`
  - `docker/frontend.Dockerfile`
  - `docker/docker-compose.yml`
- Kubernetes manifests/examples in `k8s/`:
  - API deployment
  - worker deployment
  - frontend deployment
  - namespace+secrets template
  - monitoring stack/provisioning examples

### Settings and configuration
- Central config via `recall.core.config` (environment-driven)
- Database-backed settings via settings model/repository/service
- Security-sensitive behavior configured via env variables (JWT, lockout, CORS, etc.)
- `.env.example` now exists at repository root as environment baseline template

### Device behavior (runtime)
Current inferred player/server behavior:
- device registers and heartbeats periodically
- server updates presence/status from heartbeat + metrics
- agent fetches config, downloads media, and plays cached content
- if network/API fails, agent attempts offline playback and retries with backoff
- device logs and screenshots can be uploaded

## Current architecture summary and limitations

### What exists now
- FastAPI backend with route/service/repository split in `recall-server/recall`
- SQLAlchemy models and Alembic baseline migration
- role and permission checks in API dependencies
- JWT auth endpoints with refresh/logout patterns
- Celery worker scaffolding
- React+TypeScript frontend (Vite)
- agent code already partially modular
- observability endpoints (`/health`, `/ready`, `/metrics`) and Prometheus instrumentation

### Key limitations (to resolve in enterprise rebuild)
- Repository layout is still mixed (`recall-server`, `recall-player`, `tools`, `docker`, legacy web)
- Legacy static web app still coexists with React app
- Not all enterprise domain models from target list are present/normalized
- Some auth hardening flows are partial (e.g., MFA optionality, full session revocation breadth)
- Protocol documentation and implementation naming are not fully harmonized (`device_protocol.md` vs `device-protocol.md`)
- End-to-end CI quality/security gates and release automation still need full enforcement

## Features to preserve during rebuild
- FastAPI API surface and dual-prefix compatibility (`/` and `/api/v1`)
- Device registration, heartbeat, metrics, logs, screenshots, config fetch
- Media upload with validation and malware scanning path
- Playlist, schedule, and layout primitives already present
- Alert creation/list/resolve and monitoring endpoint
- Security audit events endpoint
- JWT login/refresh/logout workflow and password hashing
- Role/permission enforcement foundations
- Multi-tenant isolation behavior currently covered by tests
- Agent offline playback + cache + retry behavior
- Existing runbooks and operational docs

## Missing enterprise features (gap list)
- Clean target repo layout rooted at `backend/`, `frontend/`, `agent/`, `deploy/`, `observability/`
- Full normalized enterprise schema for all listed entities and constraints
- Formal settings versioning + rollback workflow with complete audit coupling
- Extended auth hardening (MFA policy, stronger lock/revocation controls, advanced abuse defenses)
- Fully comprehensive RBAC matrix enforcement in services + frontend UI gating coverage
- Immutable, queryable, admin-UI audit log workflow for all critical action families
- Formally versioned device protocol contract with strict schema compatibility lifecycle
- Fully hardened enterprise agent modules (recovery, watchdog, updater compatibility checks, systemd hardening profile)
- Complete media pipeline (async transcode/thumbnail/scanning pipeline with abstraction for S3-compatible storage)
- Industrial playlist/scheduling/layout resolvers with preview and conflict simulation UX
- Fleet-scale provisioning, bulk actions, health scoring, and deep filtering
- Alert rules engine + notification channels + acknowledgement lifecycle
- Mature async job platform (retry policy, dead-letter visibility, task observability)
- Full OTA staged rollout + rollback orchestration and tracking
- Full observability stack-as-code (Prometheus, Grafana, Loki dashboards + runbooks)
- Production-grade deployment targets (compose prod, k8s/helm, backup/restore automation)
- Broad automated testing strategy with coverage targets and e2e critical flows
- Strict CI/CD quality/security gates + release artifact automation
- Complete enterprise repo hygiene, onboarding, and architecture documentation completeness

## Enterprise migration progress snapshot
- Enterprise target roots aanwezig: `backend/`, `frontend/`, `agent/`, `deploy/`, `docs/`, `.github/`, `observability/`.
- Legacy backend bron is overgezet naar `backend/app/` (transitional copy) zodat nieuwe ontwikkeling in de doellocatie kan starten.
- Legacy agent bron is overgezet naar `agent/` (transitional copy) als basis voor verdere modularisatie en hardening.

## Freeze checklist result
- [x] Baseline branch created for enterprise rebuild: `enterprise-platform`
- [x] Technical baseline documented (this file)
- [x] Preserve-feature list documented
- [x] Missing enterprise-feature gap list documented

Zie ook voortgangsregistratie: `docs/enterprise-execution-status.md`.
