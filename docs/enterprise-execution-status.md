# Enterprise Rebuild Execution Status (Steps 1–27)

_Last updated: 2026-03-10 (volledige hercontrole + uitvoeringsvolgorde)_

## Direct answer
Nee. Niet alle 27 stappen zijn volledig doorlopen en afgerond.

## Verificatie op deze vraag ("zijn alle stappen doorlopen en opgelost/aangepast?")
- **Doorlopen:** Ja, alle stappen 1 t/m 27 zijn opnieuw stuk-voor-stuk nagelopen.
- **Volledig opgelost/aangepast:** Nee, nog niet.
- **Nu direct aangepast:** status en uitvoeringsvolgorde aangescherpt met expliciete prioriteit voor de eerstvolgende uitvoerbare tranche.

## Uitvoeringsvolgorde (nu vastgezet)
1. **Tranche A (stappen 2–7):** architectuur, datamodel, settings/auth/RBAC/audit fundamentals dichtzetten.
2. **Tranche B (stappen 8–14):** device protocol, agent hardening, media, playlists/scheduling/layout/fleet end-to-end afronden.
3. **Tranche C (stappen 15–20):** alerting/workers/OTA/observability/frontend/multi-tenant productierijp maken.
4. **Tranche D (stappen 21–27):** security/deploy/teststrategie/CI-docs/features/finale acceptatie formeel aftekenen.

## Statusoverzicht per stap

| Stap | Omschrijving (kort) | Status | Opmerking |
|---|---|---|---|
| 1 | Baseline + architectuurbesluiten vastleggen | ✅ Voltooid | `docs/current-state.md` en `docs/technical-decisions.md` toegevoegd. |
| 2 | Repository herstructureren naar enterprise layout | ✅ Voltooid | Backendcode staat in `backend/app/` en agent in `agent/`. Monolithische API-entry is opgesplitst (o.a. `auth.py`/`platform.py`) én legacy onversieerde API-prefix is uitgefaseerd; routers en OAuth2 token-url verwijzen nu consequent naar `/api/v1`. |
| 3 | PostgreSQL persistentielaag + volledig datamodel | ⚠️ Gedeeltelijk | Migraties `0005_enterprise_schema_expansion.sql` en `0011_enterprise_fk_hardening.sql` dekken kern-entiteiten, auditkolommen, soft-delete/indexen en aanvullende FK/check-constraint hardening. Nieuw: SQL migratie-runner (`schema_migrations`) en idempotentie-test zijn toegevoegd; ORM/Alembic-doorvertaling en resterende datamodel-afwerking lopen nog. |
| 4 | Professioneel configuratie/settingssysteem | ⚠️ Gedeeltelijk | Settings versioning + history + rollback endpoint + security audit events zijn toegevoegd. De settingslaag ondersteunt expliciete scopes (`global`, `organization`, `device`) met strengere target-validatie (o.a. organization-scope mag geen `device_id` dragen) en uitgebreide scoped validatietests; verdere enterprise-validatieregels blijven open. |
| 5 | Enterprise-authenticatie | ⚠️ Gedeeltelijk | Password policy-validatie en account lockout-flow zijn aanwezig. Daarnaast zijn logout/logout-all, password reset request/confirm en user activation endpoints toegevoegd met refresh-token intrekking. Nieuw: reset-tokens worden alleen nog in `dev` teruggegeven (niet in productie-response) met regressietest; MFA en verdere brute-force/abuse hardening blijven open. |
| 6 | RBAC + permissions end-to-end | ⚠️ Gedeeltelijk | Permission normalisatie (`.`/`:` + aliasen), uitbreiding met `superadmin`, extra service-level enforcement (o.a. device bulk actions) en aangescherpte organization-access guardrails zijn toegevoegd met RBAC-tests; volledige matrix + frontend coverage blijft open. |
| 7 | Volledige audit logging | ⚠️ Gedeeltelijk | Immutability-migratie (DB triggers), audit-log query endpoint (`/security/audit/logs`) en settings-change/rollback audit events zijn toegevoegd. Audit-search/filtering is uitgebreid (actor/resource/ip/tijdsvenster) en auth-routes (`logout`, `logout-all`, `password-reset`, `activate`) schrijven nu ook audit logs met regressietest; volledige kritieke-actie-dekking + admin UI blijft open. |
| 8 | Formeel versioned device protocol | ⚠️ Gedeeltelijk | Protocol v1 document is aangescherpt en endpoints voor command fetch/ack + playback-status zijn toegevoegd met schema-validatie. Device-capabilities worden opgeslagen bij register en status-afleiding ondersteunt online/stale/offline/error. Nieuw: device protocol-version headerguard (`X-Device-Protocol-Version`) valideert momenteel expliciet v1 op kritieke device endpoints met route-tests; volledige lifecycle governance blijft open. |
| 9 | Robuuste enterprise agent | ⚠️ Gedeeltelijk | Agent heeft lokale health-status, event-logging, playback-status push en recovery-failure tracking naast caching/offline/retry. Nieuw: recovery thresholds (window/max failures) zijn nu configureerbaar via env en policygedrag is getest; systemd service wijst naar het nieuwe `agent/` pad. Verdere hardening/updater-compatibiliteit blijft open. |
| 10 | Veilige schaalbare mediapipeline | ⚠️ Gedeeltelijk | Duplicate-detectie op checksum, media-version registratie, metadata-inspectie (codec/resolutie/grootte/checksum) en corrupt-image detectie zijn toegevoegd. Storage abstraction (local backend) is aanwezig en heeft nu expliciete path-traversal bescherming met tests; volledige async workers/transcoding/S3-uitwerking blijft open. |
| 11 | Echte playlist engine | ⚠️ Gedeeltelijk | Playlist assignments, rules en device resolver met schedule-precedence + fallback zijn toegevoegd incl. tests. Playlist-items ondersteunen `web_url` en `widget` contenttypes met transition settings en speelbaarheidsvalidatie. Nieuw: strengere inputvalidatie op `source_url` (absolute http/https) en `widget_config` (geldig JSON object) met regressietests; volledige enterprise UX-flow blijft open. |
| 12 | Scheduling engine | ⚠️ Gedeeltelijk | Priority-aware schedule resolver en preview endpoint zijn toegevoegd. Schedule exceptions en blackout windows zijn geïmplementeerd in service/API + tests. Nieuw: recurrence-validatie is aangescherpt (alleen ondersteunde patronen, weekday-range 0–6, normalisatie) met regressietests; volledige planner-UX blijft open. |
| 13 | Layouts en zones | ⚠️ Gedeeltelijk | Zone CRUD, zone→playlist assignment en layout preview-endpoint zijn toegevoegd in backend incl. tests. Zone playback plan resolver is aangescherpt: gebruikt nu de nieuwste layout als baseline en valt terug op device-playlist als zone geen assignment heeft (getest); frontend preview-UX verfijning blijft open. |
| 14 | Fleet management | ⚠️ Gedeeltelijk | Device groups/bulkacties zijn aanwezig. Device tags en fleet filters (status/group/tag/version/last_seen) zijn toegevoegd; filter-validatie is aangescherpt (status allowlist + robuuste `last_seen_before` parsing incl. Zulu) met route-tests. Complete enterprise fleet-UX en provisioning flow nog niet volledig af. |
| 15 | Alerting + incidentdetectie | ⚠️ Gedeeltelijk | Alerts aanwezig. Nieuw: severity/status-validatie is aangescherpt (level allowlist, status allowlist), inclusief acknowledge→resolve lifecycle endpoint en regressietests; complete rule engine en notificatiekanalen moeten verder worden uitgebreid. |
| 16 | Asynchrone workers | ⚠️ Gedeeltelijk | Celery/Redis fundament aanwezig. Nieuw: retry-policy is aangescherpt (autoretry/backoff/jitter/max_retries), worker prefetch/acks-late zijn geconfigureerd en er is een workers visibility endpoint (`/workers/status`) met tests; volledige taakset en operational maturity uitbreiden. |
| 17 | OTA update infrastructuur | ⚠️ Gedeeltelijk | OTA bouwstenen aanwezig; staged rollouts/rollback-tracking/compatibiliteitsgovernance completeren. |
| 18 | Enterprise observability | ⚠️ Gedeeltelijk | Health/ready/metrics bestaan; volledige Grafana/Loki dashboards + runbooks verder formaliseren. |
| 19 | Frontend herbouw enterprise webapp | ⚠️ Gedeeltelijk | React+TS basis bestaat; volledige schermset en mature UX-patronen nog niet 100% afgerond. |
| 20 | Multi-tenant support | ⚠️ Gedeeltelijk | Tenant-isolatie aanwezig in delen + tests, maar volledige domeindekking en scoping moet verder worden afgemaakt. |
| 21 | Security hardening end-to-end | ⚠️ Gedeeltelijk | Security-basiseisen deels aanwezig; volledige deployment/process hardening set nog niet aantoonbaar compleet. |
| 22 | Productierijpe deployment | ⚠️ Gedeeltelijk | Docker/K8s aanwezig; volledige prod compose, release automation, backup/restore & rolloutstrategie aanscherpen. |
| 23 | Volledige teststrategie | ⚠️ Gedeeltelijk | Er zijn tests, maar volledige coverage-doelstelling + complete matrix nog niet volledig gehaald/aangetoond. |
| 24 | CI/CD + quality gates | ⚠️ Gedeeltelijk | Er is volwassenheid aanwezig, maar volledige gevraagde gates/tooling-combinatie en releasepad moeten worden geverifieerd/afgemaakt. |
| 25 | Documentatie + repo hygiene | ⚠️ Gedeeltelijk | Veel docs aanwezig, maar volledige set + consistentie + onboarding/releaseflow kan nog strakker. |
| 26 | Extra enterprise productfeatures | ⚠️ Gedeeltelijk | Meerdere features bestaan deels; complete volwassen set nog niet volledig afgerond. |
| 27 | Finale hardening + acceptatie | ❌ Niet voltooid | Volledige security/load/failover/disaster-acceptatiefase nog niet eind-to-end bevroren als v1.0. |

## Conclusie
- **Volledig afgerond:** stappen 1 en 2.
- **Grotendeels/ gedeeltelijk aanwezig:** meerdere stappen 3–26 met verschillende volwassenheidsniveaus.
- **Nog niet volledig eind-afgerond volgens de opgelegde definitie:** stappen 3–27.

## Uitgevoerde actie op deze feedbackronde
Alle 27 stappen zijn opnieuw doorlopen en gevalideerd op basis van de actuele code/docs/testset. Conclusie is bijgewerkt: stappen 1 en 2 zijn volledig afgerond en stappen 3–27 staan nog (deels) open. Op verzoek is daarom hieronder een concreet remediatieplan per open stap toegevoegd.

## Remediatieplan per open stap (bevestigd en geprioriteerd)

| Stap | Focus om naar ✅ te brengen | Concreet bewijs dat verplicht wordt |
|---|---|---|
| 2 | Legacy API-paden uitfaseren en route-splitsing afronden | ✅ Afgerond in deze iteratie: routers alleen onder `/api/v1` + API-testpad bijgewerkt |
| 3 | ORM/Alembic volledig in lijn met SQL migraties | Ingang gezet: SQL migratie-runner + idempotentie smoke test aanwezig; Alembic revisions nog open |
| 4 | Settings-validatie voor alle scopes afronden | Ingang gezet: extra negatieve/positieve scoped validatietests toegevoegd; verdere enterprise-validatieregels open |
| 5 | MFA + abuse-hardening toevoegen | Ingang gezet: reset-token response hardening + test toegevoegd; MFA endpoints + verdere abuse-controls blijven open |
| 6 | Volledige RBAC-matrix (backend + frontend) afronden | Ingang gezet: extra organization-access RBAC guardrails + tests toegevoegd; volledige matrix/documentatie nog open |
| 7 | Auditdekking voor alle kritieke acties 100% | Ingang gezet: auth-endpoints loggen nu expliciet audit-acties + tests; volledige kritieke matrix nog open |
| 8 | Device protocol lifecycle governance afmaken | Ingang gezet: protocol-version headervalidatie (v1) + route-tests toegevoegd; vnext compat-policy nog open |
| 9 | Agent hardening/updater-compatibiliteit afronden | Ingang gezet: configureerbare recovery-policy + tests toegevoegd; updater-compatibiliteit/runbook nog open |
| 10 | Async media workers + transcoding + S3 afronden | Ingang gezet: local storage path-hardening + tests; worker queue/transcoding/S3 integratie nog open |
| 11 | Playlist UX-flow en enterprise editor afronden | Ingang gezet: strengere web_url/widget inputvalidatie + tests; enterprise editor/UX en acceptance nog open |
| 12 | Planner UX + uitzonderingsbeheer afronden | Ingang gezet: recurrence-validatie en normalisatie + tests toegevoegd; volledige planner-UX/e2e nog open |
| 13 | Layout preview UX afronden | Ingang gezet: zone-plan resolver verbeterd (latest-layout + fallback) met tests; UI regressietests/preview nog open |
| 14 | Fleet provisioning en enterprise UX afronden | Ingang gezet: fleet filter-validatie hardening + route-tests; lifecycle e2e/UX en bulk-action audits nog open |
| 15 | Rule engine + severity lifecycle afronden | Ingang gezet: alert severity/status-validatie + ack/resolve lifecycle tests toegevoegd; rule engine/notificatiecontracten nog open |
| 16 | Worker retry/visibility production-grade maken | Ingang gezet: retry/backoff configuratie + `/workers/status` visibility endpoint/tests; dead-letter dashboards en volledige taakset nog open |
| 17 | Staged OTA rollouts met rollback governance | Ingang gezet: staged rollout-controls (rollout_percentage/dry_run) en semver-compatibiliteitschecks voor update/rollback + tests; volledige OTA governance/runbook blijft open |
| 18 | Grafana/Loki dashboards + runbooks finaliseren | Ingang gezet: `/observability/summary` endpoint voor devices/alerts/workers operationele samenvatting + API-tests; Grafana/Loki dashboard exports en runbooks nog open |
| 19 | Frontend schermset en UX-patronen afronden | Ingang gezet: nieuwe frontend `Observability` pagina met herbruikbare stat-cards, worker tabel en refresh UX op `/api/v1/observability/summary`; build + screenshot vastgelegd, volledige schermset/e2e blijft open |
| 20 | Tenant-scope op alle domeinen afdwingen | Ingang gezet: observability endpoints tenant-scope-aware gemaakt (org users scoped, global admin aggregate-all, unscoped non-admin geblokkeerd) met API-tests; volledige domeinbrede isolatiematrix blijft open |
| 21 | Security hardening (deploy/process) afronden | Ingang gezet: host-header allowlist, configureerbaar trust-beleid voor `X-Forwarded-Proto`, en HSTS-header bij HTTPS-enforcement met regressietests; volledige deploy/process hardening + pentesttraject blijft open |
| 22 | Release automation + backup/restore valideren | Ingang gezet: SQLite backup/restore helper + tests + runbook drillstappen én release-workflow gates (tag-policy check, backend smoke tests, frontend build) toegevoegd; volledige productie-DR validatie blijft open |
| 23 | Teststrategie naar doelcoverage brengen | Ingang gezet: coverage CI met backend+agent `pytest-cov` gates, XML artifacts én per-module threshold checks (`tools/coverage_threshold_check.py`) met baseline-documentatie; volledige matrix-uitbouw blijft open |
| 24 | CI/CD quality gates volledig afdwingen | Ingang gezet: GitHub workflows gecorrigeerd naar actuele `backend/` paden met werkende lint/type/test en security scans (Bandit + pip-audit) als gate-basis; volledige required-check policy/release gates blijven open |
| 25 | Docs consistentie/onboarding/releaseflow afronden | Ingang gezet: automatische docs-lint workflow + `tools/doc_lint.py` en expliciet onboarding dry-run runbook toegevoegd; volledige releaseflow-consistentie en bredere docset-audit blijven open |
| 26 | Extra enterprise features productierijp maken | Ingang gezet: fleet inventory exportfeature toegevoegd (`/api/v1/device/export.csv`) met filterondersteuning en route-tests; bredere set enterprise productfeatures + acceptatiecriteria blijft open |
| 27 | Finale acceptatiefase (security/load/failover/DR) | Ingang gezet: formeel v1.0 sign-off runbook + acceptance checker (`tools/acceptance_check.py`) + test toegevoegd; daadwerkelijke ingevulde evidence en finale go/no-go blijven open |

## Uitgevoerde actie op deze feedbackronde
Alle 27 stappen zijn opnieuw doorlopen en gevalideerd op basis van de actuele code/docs/testset. Conclusie blijft dat stap 1 volledig afgerond is en stappen 2–27 nog (deels) open staan. Op verzoek is daarom hieronder een concreet remediatieplan per open stap toegevoegd.

## Remediatieplan per open stap (nu toegevoegd)

| Stap | Focus om naar ✅ te brengen | Concreet bewijs dat verplicht wordt |
|---|---|---|
| 2 | Legacy API-paden uitfaseren en route-splitsing afronden | Verwijderde legacy importpaden + routeregistratie-tests |
| 3 | ORM/Alembic volledig in lijn met SQL migraties | Alembic revisions + migration smoke test in CI |
| 4 | Settings-validatie voor alle scopes afronden | Negatieve/positieve validatietests per scope |
| 5 | MFA + abuse-hardening toevoegen | MFA endpoints + lockout/rate-limit e2e tests |
| 6 | Volledige RBAC-matrix (backend + frontend) afronden | Matrixdocument + permission coverage tests |
| 7 | Auditdekking voor alle kritieke acties 100% | Audit assertions per kritieke endpoint/service |
| 8 | Device protocol lifecycle governance afmaken | Versioning policy + compat-tests v1/vnext |
| 9 | Agent hardening/updater-compatibiliteit afronden | Recovery/updater integrietests + runbook |
| 10 | Async media workers + transcoding + S3 afronden | Worker queue tests + storage integration tests |
| 11 | Playlist UX-flow en enterprise editor afronden | Frontend acceptance tests + playable snapshots |
| 12 | Planner UX + uitzonderingsbeheer afronden | Planner e2e tests incl. blackout/exceptions |
| 13 | Layout preview UX afronden | UI regressietests + preview screenshots |
| 14 | Fleet provisioning en enterprise UX afronden | Device lifecycle e2e + bulk-action audits |
| 15 | Rule engine + severity lifecycle afronden | Alert simulation tests + notificatiecontracten |
| 16 | Worker retry/visibility production-grade maken | Dead-letter/retry dashboards + tests |
| 17 | Staged OTA rollouts met rollback governance | Rollout scenario tests + compatibiliteitsmatrix |
| 18 | Grafana/Loki dashboards + runbooks finaliseren | Dashboard exports + on-call runbooks |
| 19 | Frontend schermset en UX-patronen afronden | DoD checklist + visual/e2e testresultaten |
| 20 | Tenant-scope op alle domeinen afdwingen | Tenant-isolatie testmatrix (API + DB) |
| 21 | Security hardening (deploy/process) afronden | Hardening checklist + pentest bevindingen |
| 22 | Release automation + backup/restore valideren | Disaster-recovery oefening + release pipeline bewijs |
| 23 | Teststrategie naar doelcoverage brengen | Coverage rapport + ontbrekende suites aangevuld |
| 24 | CI/CD quality gates volledig afdwingen | Required checks + blokkering bij gate failure |
| 25 | Docs consistentie/onboarding/releaseflow afronden | Doc lint + onboarding dry-run |
| 26 | Extra enterprise features productierijp maken | Feature DoD + acceptance criteria per feature |
| 27 | Finale acceptatiefase (security/load/failover/DR) | Geformaliseerd sign-off dossier v1.0 |

## Afspraak voor vervolg
Voor iedere volgende wijziging wordt dit statusdocument mee bijgewerkt zodat zichtbaar blijft welke stap exact van ⚠️ naar ✅ gaat met verifieerbaar bewijs (code, tests, docs, migraties én operationele artefacten).
