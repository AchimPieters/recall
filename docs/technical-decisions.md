# Technical Decisions for Enterprise Rebuild

Status: **Accepted**  
Date: 2026-03-08

## Decision 1: Backend framework
- **Decision:** Backend remains **FastAPI**.
- **Rationale:** Existing codebase, API patterns, dependency injection, and async ecosystem are already centered on FastAPI.

## Decision 2: Primary database
- **Decision:** Primary datastore is **PostgreSQL**.
- **Rationale:** Strong relational guarantees, indexing, constraints, migration tooling, and enterprise operational maturity.

## Decision 3: Queue and background processing
- **Decision:** Use **Redis + Celery**.
- **Rationale:** Current worker direction aligns with Celery; Redis serves as broker/cache and scales operationally.

## Decision 4: Frontend stack
- **Decision:** Frontend is **React + TypeScript**.
- **Rationale:** Existing Vite+React foundation and required enterprise UI complexity benefit from typed component architecture.

## Decision 5: Observability stack
- **Decision:** Use **Prometheus + Grafana + Loki**.
- **Rationale:** Covers metrics, dashboards, and centralized logs with strong Kubernetes and container ecosystem support.

## Decision 6: Version policy
- **Decision:** Adopt **Semantic Versioning (SemVer)** for all release artifacts starting now.
- **Policy:**
  - Format: `MAJOR.MINOR.PATCH`.
  - `MAJOR`: breaking API/protocol or incompatible behavior changes.
  - `MINOR`: backward-compatible feature additions.
  - `PATCH`: backward-compatible fixes only.
  - Pre-release tags allowed (`-alpha`, `-beta`, `-rc.N`) for staged rollouts.
  - Git tags must match released version numbers.

## Immediate architectural guardrails
- No large monolithic `server.py` growth for new business logic.
- New backend logic follows route -> service -> repository separation.
- Cross-cutting concerns (config/auth/security/logging) live under a dedicated core module.
- Enterprise rebuild execution follows the ordered migration plan captured in the request.
