# Current State Baseline (Frozen)

_Last updated: 2026-03-09_
_Baseline branch: `enterprise-platform`_

## 1. Doel van deze baseline
Deze baseline bevriest de huidige technische situatie voordat verdere enterprise-herbouwstappen worden uitgevoerd. Het doel is expliciet: **geen chaotische verbouwing zonder vaste architectuurkeuzes**.

## 2. Volledige inventarisatie van de huidige codebase

### 2.1 Backend endpoints (FastAPI)
De API wordt gemount op zowel root als `/api/v1`.

- Platform/core:
  - `GET /`
  - `GET /health`
  - `GET /live`
  - `GET /ready`
  - `GET /version`
  - `GET /metrics`
- Auth/security:
  - `POST /token`
  - `POST /auth/login`
  - `POST /token/refresh`
  - `POST /auth/refresh`
  - `POST /auth/logout`
  - `POST /auth/logout-all`
  - `POST /auth/password-reset/request`
  - `POST /auth/password-reset/confirm`
  - `POST /auth/activate`
  - `GET /audit-logs`
  - `GET /security/audit`
  - `GET /security/audit/logs`
- Devices/protocol/fleet:
  - `POST /device/register`
  - `POST /device/heartbeat`
  - `GET /device/config`
  - `POST /device/logs`
  - `GET /device/logs`
  - `POST /device/screenshot`
  - `GET /device/screenshots`
  - `POST /device/metrics`
  - `POST /device/commands/enqueue`
  - `GET /device/commands`
  - `POST /device/command-ack`
  - `POST /device/playback-status`
  - `GET /device/list`
  - `POST /device/groups`
  - `GET /device/groups`
  - `POST /device/groups/{group_id}/bulk`
  - `POST /device/groups/{group_id}/members`
  - `POST /device/tags`
  - `GET /device/tags`
  - `POST /device/tags/assign`
- Media:
  - `POST /media/upload`
  - `GET /media`
- Playlists/scheduling/layouts:
  - `POST /playlists`
  - `GET /playlists`
  - `POST /playlists/{playlist_id}/items`
  - `GET /playlists/{playlist_id}/items`
  - `POST /playlists/{playlist_id}/schedule`
  - `POST /playlists/schedules`
  - `POST /playlists/schedules/{schedule_id}/exceptions`
  - `POST /playlists/schedules/blackouts`
  - `GET /playlists/schedules/resolve/preview`
  - `POST /playlists/resolve/at`
  - `GET /playlists/resolve/preview`
  - `GET /playlists/resolve/device/{device_id}`
  - `POST /playlists/layouts`
  - `POST /playlists/layouts/{layout_id}/zones`
  - `POST /playlists/zones/{zone_id}/playlist`
  - `GET /playlists/layouts/{layout_id}/preview`
  - `GET /playlists/layouts`
- Settings:
  - `GET /settings`
  - `POST /settings`
  - `POST /settings/apply`
  - `GET /settings/history`
  - `POST /settings/rollback`
- Monitoring/events/system:
  - `GET /monitor`
  - `POST /monitor/alerts`
  - `GET /monitor/alerts`
  - `POST /monitor/alerts/{alert_id}/resolve`
  - `GET /events`
  - `POST /system/reboot`
  - `POST /system/update`

### 2.2 Agent functionaliteit (huidig)
De agent is modulair opgezet (`agent/agent_modules` en `recall-player/agent_modules`) met o.a.:
- config en auth initialisatie
- device registratie + heartbeat
- config polling
- media downloader/cache
- player + scheduler paden
- metrics/logging/screenshot paden
- updater/watchdog/recovery-gerichte modules (incl. lokale recovery failure tracking)
- offline playback/fallback gedrag met reconnect/backoff

### 2.3 Webpagina’s
Er bestaan twee UI-lagen:
- Legacy static pagina’s in `recall-server/web/`:
  - `index.html`, `devices.html`, `media.html`, `monitor.html`, `settings.html`
- React + TypeScript frontend in `frontend/src/pages/`:
  - Dashboard, Devices, Media, Playlists, Schedules, Alerts, Audit Logs, Settings

### 2.4 Docker setup
- `docker/Dockerfile` (backend)
- `docker/frontend.Dockerfile` (frontend)
- `docker/docker-compose.yml` (dev stack)
- Kubernetes manifests/templates onder `k8s/` (api, worker, frontend, monitoring/secrets voorbeelden)

### 2.5 Settings
- Centrale configlaag op basis van environment variabelen (`backend.app.core.config`)
- Database-backed settings + history/rollback paden aanwezig met expliciete scopes: global, organization en device
- Security- en auth-gerelateerde instellingen centraal geconfigureerd
- Root `.env.example` aanwezig als baseline

### 2.6 Device gedrag
- Device registreert zich en verstuurt periodiek heartbeat/metrics
- Server leidt presence/status af en bewaart logs/screenshots
- Device kan config ophalen (incl. zone_plan), en commands fetchen + ack terugsturen
- Playback-status wordt server-side geregistreerd
- Agent hanteert retry/backoff en offline cache-afspeelpad

## 3. Huidige architectuur (kort) + beperkingen

### Wat bestaat nu
- FastAPI backend met route/service/repository scheiding in `backend/app`
- SQLAlchemy-modellen + migraties (incl. enterprise-uitbreidingen)
- JWT auth + refresh + lockout/rate-limit fundament
- RBAC/permission dependencies
- React + TypeScript frontend (Vite)
- Modulaire agentcode
- Celery workers + Redis richting
- Health/readiness/metrics + observability fundament

### Belangrijkste beperkingen
- Legacy en nieuwe paden bestaan nog naast elkaar (`recall-server`, `recall-player` vs `backend`, `agent`)
- Niet alle enterprise-workflows zijn volledig doorgevoerd in UI en operationele processen
- Dubbele documentatiebestanden voor device protocol bestaan nog (`device_protocol.md` en `device-protocol.md`)
- Volledige kwaliteitsgates/release-automatisering en hardening zijn nog niet uniform afgedwongen over alle onderdelen

## 4. Features die behouden moeten blijven
- FastAPI als backend runtime + dual prefix API mounting
- Device register/heartbeat/config/metrics/logs/screenshots/commands/playback-status
- Media upload + validatie/scanning pipeline met metadata-inspectie en corrupt-upload detectie
- Playlist/schedule/layout fundament en resolvers
- Settings versiebeheer + rollback
- Monitoring + alerts + events
- JWT auth + refresh + lockout fundamentals
- RBAC/permissions en tenant-isolatie basis
- Agent offline playback/cache/reconnect/watchdog basis
- Bestaande runbooks en operationele documentatie

## 5. Ontbrekende enterprise-features (gaplijst)
- Volledige consolidatie naar één canonical codepad (legacy volledig uitfaseren)
- Verdere normalisatie/constraints van volledig enterprise datamodel en lifecycle governance
- Breder afgedekte enterprise-auth flows (MFA afdwinging, complete session revocation matrix)
- End-to-end permission enforcement inclusief frontend zichtbaarheid per actie
- Immutable audit logging voor alle kritieke domeinacties + rijk admin UI gebruikspaden
- Volledig geformaliseerd versioned device protocol met compatibiliteitsbeleid
- Volledige media pipeline op workerschaal (scan/transcode/thumbnail/S3-abstractie + DLQ observability)
- Fleet management op grote schaal (provisioning, health score, geavanceerde bulk workflows)
- OTA staged rollouts met sterke rollback- en compatibiliteitscontroles
- Productieklare deployment- en releaseautomatisering met recovery-oefeningen
- Hogere, aantoonbare testdekking op kernlogica + kritieke e2e-flows

## 6. Freeze check
- [x] Nieuwe hoofdbrach voor herbouw: `enterprise-platform`
- [x] Volledige inventarisatie vastgelegd
- [x] Huidige architectuur + beperkingen vastgelegd
- [x] Behoud-lijst van features vastgelegd
- [x] Gap-lijst van ontbrekende enterprise features vastgelegd
