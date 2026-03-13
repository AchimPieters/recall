# Enterprise fase-audit (2026-03-12)

## Scope en methode
Deze audit controleert de 5 fasen uit de restlijst lineair (fase 1 → 5), met code- en CI-evidence op repositoryniveau.

Uitgevoerde controle-commando's:
- `find . -maxdepth 2 -type d`
- `rg -n "recall-server|Base\.metadata\.create_all|ALTER TABLE|/api/v1" backend docs .github`
- `rg -n "syft|grype|cosign|OpenTelemetry|staging|release" .github/workflows docs k8s`
- `test -f docs/api-versioning.md ...`

## Auditresultaat per fase

## Fase 1 — Architectuur
1. **Legacy runtime verwijderen** — **GROTENDEELS VOLTOOID**
   - `recall-server/` map ontbreekt.
   - Runtime code draait vanuit `backend/`.
   - Historische verwijzingen bestaan nog in oudere auditdocumenten.

2. **Runtime schema mutaties verwijderen** — **VOLTOOID (runtime), TESTS NOG HYBRIDE**
   - In runtime code geen `Base.metadata.create_all` of runtime `ALTER TABLE` gevonden.
   - DDL-mutaties zitten in SQL-migraties onder `backend/app/db/migrations/`.
   - Enkele tests gebruiken nog `Base.metadata.create_all` voor in-memory setup; dit is test-only.

3. **Domain events introduceren** — **VOLTOOID (basis)**
   - Event infrastructuur aanwezig in `backend/app/core/events/` en worker handlers in `backend/app/workers/event_handlers.py`.

4. **API versioning `/api/v1`** — **VOLTOOID**
   - Router mounting via `/api/v1` in `backend/app/api/main.py`.
   - Public API aanwezig op `/api/public/v1`.
   - Versioning document aanwezig: `docs/api-versioning.md`.

5. **Domain layer toevoegen** — **VOLTOOID (basis), VERDIEPING OPEN**
   - `backend/app/domain/` bestaat met domeinlogica voor playlist/device assignment.
   - Architectuurlijn is aanwezig, maar nog niet overal uniform diep uitgewerkt.

## Fase 2 — Security
6. **MFA** — **VOLTOOID (basis)**
   - MFA core + auth endpoints en tests aanwezig.

7. **Device provisioning hardening** — **GROTENDEELS VOLTOOID**
   - Provisioning migraties en routes aanwezig; cert/mTLS opties deels voorbereid.

8. **Secret management** — **VOLTOOID (documentatie + scheduler basis)**
   - Secret management document aanwezig (`docs/secrets-management.md`) en rotatieservice in backend.

9. **Supply chain security** — **VOLTOOID (CI basis)**
   - Workflow met syft/grype/cosign aanwezig.

10. **Upload sandboxing** — **VOLTOOID (basis)**
   - Upload-validaties en mime/structuur checks aanwezig in media pipeline.

## Fase 3 — Operations
11. **Staging omgeving** — **VOLTOOID (basis)**
   - `dev -> staging -> production` documentatie en workflow aanwezig.

12. **Release pipeline** — **GROTENDEELS VOLTOOID**
   - Release workflow + changelog/tag gates aanwezig.

13. **Disaster recovery automatiseren** — **GROTENDEELS VOLTOOID**
   - Code voor backup/restore helpers + tests bestaat.
   - Formeel DR-runbook aanwezig: `docs/disaster-recovery.md`.
   - Kubernetes voorbeeldautomatisering toegevoegd: `k8s/disaster-recovery-cronjobs.example.yaml`.

14. **Distributed tracing** — **VOLTOOID (basis)**
   - OpenTelemetry init aanwezig; documentaire backendverwijzingen naar Jaeger/Tempo aanwezig.

15. **Agent in compose stack** — **VOLTOOID**
   - `docker/docker-compose.yml` bevat `recall-agent` service.

## Fase 4 — Maintainability
16. **Coverage >85%** — **GROTENDEELS VOLTOOID**
   - Nieuwe gecombineerde coverage-gate in CI dwingt `backend/app + agent` af op minimaal 85%.
   - Lokale verificatie: `pytest -q backend/tests agent/tests --cov=backend/app --cov=agent --cov-fail-under=85` slaagt.

17. **Architectural tests** — **VOLTOOID (basis)**
   - Boundary tests aanwezig (`backend/tests/test_architecture_boundaries.py`).

18. **Frontend engineering maturity** — **VOLTOOID (basis)**
   - Vite/Vitest + frontend tests aanwezig.

19. **Developer onboarding** — **VOLTOOID**
   - `docs/developer-onboarding.md` aanwezig.

20. **Dependency governance** — **VOLTOOID**
   - `docs/dependency-policy.md` aanwezig.

## Fase 5 — Product maturity
21–26. **Status: GEDEELTELIJK (met extra release-voortgang)**
- Content workflow, analytics, public API, edge reliability en enterprise UX hebben duidelijke voortgang.
- Product-release notes toegevoegd voor `v1.0.0` en `v1.1.0` (`CHANGELOG.md` + `docs/releases/*`).
- Volledige 10/10 afronding (release hardening + volledige E2E maturity) staat nog open.

## Conclusie en eerstvolgende stap
- Fase 3 stap 13 is nu ingevuld op documentatie + voorbeeld-automatisering.
- Eerstvolgende zware openstaande items zitten nu vooral in fase 5: volledige productmaturity hardening en release-acceptatie op enterprise-niveau.
