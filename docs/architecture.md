# Recall v2 Enterprise Architecture

## 1) High-level platform architecture
Recall evolves to a 4-tier platform:

1. **Web UI (React + TypeScript + Vite)** for operators/admins.
2. **API Gateway (FastAPI)** with authN/authZ, rate limiting and API composition.
3. **Domain APIs + Service Layer** for devices, media, playlists, scheduling, monitoring and system actions.
4. **Persistence + async platform**: PostgreSQL (state), Redis (broker/cache), Celery workers (heavy/background tasks).

```text
Web UI -> API Gateway -> Domain APIs -> Services -> Repositories/ORM -> PostgreSQL
                            |                               |
                            +-------- WebSocket/Events -----+
                            +-------- Celery tasks ---------> Redis/Workers
```

## 2) Bounded contexts and responsibilities
- **Identity & Access**: OAuth2/JWT, refresh tokens, RBAC (`admin`, `operator`, `viewer`, `device`).
- **Device Fleet**: device lifecycle, heartbeat, capability inventory, bulk operations.
- **Media Pipeline**: upload, MIME validation, virus scanning, metadata extraction, thumbnails, transcoding.
- **Playback Domain**: playlists, items, schedules, layouts, zones, fallback logic.
- **Observability**: metrics, logs, traces/events, alerts.
- **System Management**: OTA workflows, reboot/update jobs, audit history.

## 3) Service contracts (target)
- **API layer**: transport only (validation, status codes, dependency wiring).
- **Services**: business rules and orchestration.
- **Repositories**: all persistence and tenant-scoped querying.
- **Workers**: long-running/CPU-heavy workflows, never in request thread.

## 4) Data architecture
PostgreSQL is the source of truth for:
- users, organizations, devices, device_groups
- media, playlists, playlist_items, schedules
- layouts, zones, alerts, settings, audit_logs
- update_jobs, update_history

Every table that contains tenant data carries `organization_id` + query enforcement in repositories.

## 5) Security architecture
- Mandatory JWT auth (no optional API-key bypass).
- RBAC checks per endpoint.
- Account lockout + password policy.
- Secure headers at reverse proxy and app edge.
- Upload protection (MIME, size, antivirus).
- Immutable-style audit trail for critical actions.

## 6) Runtime and deployment
- **Core services**: recall-api, recall-worker, recall-web, recall-agent, postgres, redis.
- **Ingress/edge**: Traefik (TLS + security headers).
- **Observability**: Prometheus + Grafana + Loki.
- **Targets**: docker-compose (dev/prod) and Kubernetes manifests.

## 7) Migration strategy from current repo
This repository currently contains legacy `recall-server/` and static UI pages. The v2 migration is executed incrementally:
1. Keep existing runtime stable.
2. Introduce new directories and docs/contracts.
3. Move domain-by-domain into new modules.
4. Decommission legacy endpoints/UI after parity tests pass.
