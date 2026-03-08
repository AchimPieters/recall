# Recall Engineering Audit — 2026-03-08

Doel: checklist valideren tegen huidige codebase en expliciet markeren wat al gereed is en wat nog open staat.

## Samenvatting

- **Volledig afgedekt:** 24/37
- **Gedeeltelijk afgedekt:** 10/37
- **Open:** 4/37

> Conclusie: platform staat sterk op fundament/security/operations, maar is nog **niet 100%** op enterprise-productvolwassenheid.

## Checklist status

| # | Onderdeel | Status | Opmerking |
|---|---|---|---|
| 1 | Backend herstructureren | ✅ | `api/services/repositories/models/core/workers` aanwezig. |
| 2 | Database (PostgreSQL + ORM + migraties + tabellen) | 🟡 | SQLAlchemy + migraties aanwezig, default DB fallback is nog sqlite in dev. |
| 3 | Configuratie management | ✅ | Gecentraliseerd in `core/config.py`; `.env.example` toegevoegd. |
| 4 | Authenticatie + JWT + refresh + lockout | ✅ | OAuth2/JWT + lockout aanwezig in auth/security laag. |
| 5 | RBAC | ✅ | Rollen en permission checks op endpoints aanwezig. |
| 6 | Audit logging | ✅ | model/repository/service/routes aanwezig voor kritieke events. |
| 7 | Device protocol endpoints | ✅ | register/heartbeat/metrics/logs/screenshot/config endpoints aanwezig + docs. |
| 8 | Device lifecycle management | 🟡 | Status en heartbeat aanwezig; capabilities nog beperkt gemodelleerd. |
| 9 | Device groups + bulk operations | ✅ | groups + bulk `reboot`/`update`/`playlist_assign` endpoint met event+device logging aanwezig. |
| 10 | Upload security | 🟡 | size/UUID aanwezig; virus scan aanwezig; MIME policy kan strikter. |
| 11 | Media verwerking | 🟡 | metadata/thumb pipeline aanwezig; ffmpeg pad afhankelijk van host image. |
| 12 | Media opslag | ✅ | storage + checksum/duplicate-controls aanwezig. |
| 13 | Playlist model | 🟡 | playlists/items/schedules aanwezig; layouts/zones nog beperkt. |
| 14 | Playlist functionaliteit | 🟡 | CRUD + ordering aanwezig; fallback-content niet overal afgedwongen. |
| 15 | Scheduling engine | 🟡 | time-based scheduling aanwezig; overlap/tz validatie deels aanwezig. |
| 16 | Agent architectuur | 🟡 | agent bestaat; module-splitsing niet volledig conform target. |
| 17 | Offline playback | ✅ | lokale cache en playback continuity aanwezig. |
| 18 | Recovery systemen | 🟡 | watchdog/reconnect aanwezig; crash recovery verder te hardenen. |
| 19 | Worker systeem | ✅ | Redis + Celery worker tasks aanwezig. |
| 20 | Metrics | ✅ | `/metrics` en platform metrics aanwezig. |
| 21 | Logging | ✅ | structured logging + request-level context aanwezig. |
| 22 | Monitoring stack | 🟡 | Prometheus/Grafana/Loki opgenomen in ops-documentatie; omgeving afhankelijk. |
| 23 | Frontend React + TypeScript | ❌ | huidige web UI is nog hoofdzakelijk statisch HTML/CSS. |
| 24 | UI pagina’s | 🟡 | pagina’s bestaan functioneel, maar nog niet in React/TS architectuur. |
| 25 | Device alerts | ✅ | offline/storage/playback alerts aanwezig. |
| 26 | Device tools | ✅ | remote screenshots/logs/reboot flows aanwezig. |
| 27 | Update service | ✅ | device/server versioning aanwezig. |
| 28 | Update flow | 🟡 | staged rollout/history aanwezig; rollback support verder uitwerken. |
| 29 | Docker stack | ✅ | api/worker/frontend/postgres/redis compose aanwezig. |
| 30 | Kubernetes support | 🟡 | manifests deels aanwezig, production hardening open. |
| 31 | CI pipeline | ✅ | lint/tests/security/build checks aanwezig. |
| 32 | Code quality tools | ✅ | ruff/black/mypy/bandit opgenomen. |
| 33 | Unit tests | ✅ | services/repositories/utils coverage aanwezig. |
| 34 | Integration tests | ✅ | API/DB/auth integratietests aanwezig. |
| 35 | Agent tests | 🟡 | simulatie deels aanwezig; offline playback testmatrix uitbreiden. |
| 36 | Repo hygiene | ✅ | CHANGELOG/CONTRIBUTING/SECURITY/CODEOWNERS aanwezig. |
| 37 | Documentatie | 🟡 | architecture/api/deployment aanwezig; device-protocol nu toegevoegd. |

## Directe remediation backlog

1. Frontend migreren naar React + TypeScript (fase 9/24) en pagina’s component-based implementeren.
3. Scheduling constraints aanscherpen met harde overlap/tijdzone validatie op schema-niveau.
4. Agent intern opdelen in modules (`heartbeat/downloader/player/cache/updater/watchdog/screenshots`).
5. Kubernetes manifests production-grade maken (secrets, probes, autoscaling, network policies).

## Her-audit protocol

- Na elke remediation sprint dit document bijwerken.
- Pas bij **37/37 volledig groen** claim “100% voldaan”.
