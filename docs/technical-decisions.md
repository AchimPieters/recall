# Technical Decision Record — Enterprise Rebuild

Status: **Accepted**
Date: 2026-03-09

## Beslisdoel
Deze beslissingen zijn bevroren als architectuurkaders voor de enterprise-herbouw, zodat vervolgwerk niet afwijkt van fundamentele platformkeuzes.

## ADR-001 — Backend framework
- **Besluit:** Backend blijft **FastAPI**.
- **Waarom:** Huidige codebase, async-ondersteuning, dependency injection en bestaande route/service/repository patronen sluiten hierop aan.

## ADR-002 — Database
- **Besluit:** Primaire datastore wordt **PostgreSQL**.
- **Waarom:** Relationele integriteit, volwassen migratie-ecosysteem, sterke performance bij complexe query’s en tenant-isolatie.

## ADR-003 — Queue en background processing
- **Besluit:** **Redis + Celery**.
- **Waarom:** Scheiding van API-latency en zware taken (media, planning, OTA, alerts) met beproefde operationele tooling.

## ADR-004 — Frontend stack
- **Besluit:** **React + TypeScript** (Vite).
- **Waarom:** Typeveiligheid, schaalbaar componentmodel en passend voor enterprise beheerportaalcomplexiteit.

## ADR-005 — Observability stack
- **Besluit:** **Prometheus + Grafana + Loki**.
- **Waarom:** Standaardstack voor metrics, dashboards en gecentraliseerde logs met goede container/Kubernetes integratie.

## ADR-006 — Versiebeleid
- **Besluit:** Vanaf nu wordt **Semantic Versioning (SemVer)** verplicht gebruikt.
- **Beleid:**
  - Formaat: `MAJOR.MINOR.PATCH`
  - `MAJOR`: breaking changes (API/protocol/incompatibele runtime)
  - `MINOR`: backward-compatible feature uitbreidingen
  - `PATCH`: backward-compatible bugfixes
  - Pre-release tags toegestaan: `-alpha`, `-beta`, `-rc.N`
  - Release tags en artifacts volgen exact dezelfde semver-string

## Engineering guardrails (afgeleid uit besluiten)
- Geen nieuwe businesslogica in monolithische entrypoint-bestanden.
- Routes behandelen alleen request/response en auth dependencies.
- Businessregels zitten in `services/`.
- Persistence en queries zitten in `repositories/`.
- Cross-cutting concerns (config/auth/security/logging) zitten gecentraliseerd in `core/`.
