# Recall Ultra-Deep Code Audit (Current State)

Date: 2026-03-07  
Scope: Entire repository (`/workspace/recall`)

## Requested benchmark

Target asked: verify if the codebase is at:

- Architectuur: **10/10**
- Security: **10/10**
- Operations: **10/10**
- Maintainability: **10/10**
- Productvolwassenheid: **10/10**

## Verdict (short)

**No** — the repository is not at 10/10 in any of those dimensions yet.

## Method used

1. Manual review of API, services, models, scripts, docs, and web UI.
2. Automated checks:
   - `python3 -m pytest -q recall-server/tests`
   - `bandit -q -r recall-server recall-player tools -f txt`
   - `python3 -m compileall -q recall-server recall-player tools`
   - `shellcheck install.sh uninstall.sh update.sh recall-install.sh install-docker.sh install-pi.sh install-x86.sh`

---

## Scorecard

| Category | Score (/10) | Why not 10/10 |
|---|---:|---|
| Architectuur | **7.5** | Clear layering in server package, but mixed legacy/runtime paths and split server modes (FastAPI + Flask dev server) create drift and ambiguity. |
| Security | **6.5** | Good role-based JWT and upload checks exist, but insecure defaults and trust-boundary gaps remain (default JWT secret, permissive CORS, bootstrap admin creds). |
| Operations | **6.0** | Health/readiness/metrics and Docker/systemd exist, but deployment consistency, secret handling, backup/migration workflow, and production runbooks are incomplete. |
| Maintainability | **7.0** | Modular package and tests exist, but test depth is shallow, dependency pinning absent, and deprecated APIs/warnings are unresolved. |
| Productvolwassenheid | **6.0** | Core features work, but maturity signals (SLOs, observability strategy, release governance, hardening baselines) are still early-stage. |

---

## Category deep dive

## 1) Architectuur — 7.5/10

### What is good
- Layer separation is explicit and mostly respected (`api/routes` → `services` → `models`/`db`).
- Config/auth/security concerns are centralized under `recall/core`.
- Docs describe intended layered architecture.

### Why this is not 10/10
1. **Dual server patterns** remain in repo (production FastAPI app and separate Flask dev server), increasing cognitive load and risk of behavior drift.
2. **Schema ownership is mixed**: DB bootstrapping uses `Base.metadata.create_all(...)` while SQL migration SQL also exists, which can diverge over time.
3. **Domain boundaries are thin** in places (direct dict payloads in settings and device routes) with limited typed contracts for full API surface.

### Architectural risk
- Medium: maintainers can unintentionally change one runtime path while assumptions in docs/scripts still point to another path.

---

## 2) Security — 6.5/10

### What is good
- JWT-based auth and role gates are in place on protected routes.
- Login endpoint has rate limiting.
- Upload flow validates size/MIME and uses generated UUID filenames.
- Optional ClamAV streaming scan hook exists.

### Gaps blocking 10/10
1. **Unsafe default secret** (`JWT_SECRET` defaults to `change-me`) makes accidental weak deployments possible.
2. **Bootstrap admin account** is created with `admin/admin` on startup if missing.
3. **CORS wildcard** (`allow_origins=["*"]`, allow all methods/headers) is too permissive for production.
4. **Malware scan fail-open behavior** currently returns success when ClamAV is unreachable.
5. **No explicit transport hardening** (TLS termination assumptions not enforced in app-level config/docs).

### Security risk
- Medium-to-high for default installs; significantly lower only after operator hardening.

---

## 3) Operations — 6.0/10

### What is good
- `/health`, `/ready`, and Prometheus `/metrics` endpoints exist.
- Structured request logging via `structlog` is enabled.
- Container and systemd assets are present.

### Gaps blocking 10/10
1. **Production configuration discipline** is weak (un-pinned requirements, placeholder secrets in compose).
2. **Migration operations** are under-defined: migration SQL exists but no clear, enforced migration execution lifecycle in deploy docs.
3. **Runbooks/incident guidance** are minimal (no defined backup/restore, rollback, alerting thresholds).
4. **Service topology docs** mention planned components that are not actually implemented, which can confuse operations.

### Operational risk
- Medium: likely fine for small/internal deployments, but underpowered for strict production reliability expectations.

---

## 4) Maintainability — 7.0/10

### What is good
- Codebase is relatively compact and readable.
- Service-level separation reduces route complexity.
- Basic tests exist and pass.
- Shell scripts pass shellcheck in current state.

### Gaps blocking 10/10
1. **Test coverage depth** is limited (few integration/negative/security tests).
2. **Deprecation warnings** surfaced in tests (`on_event`, `datetime.utcnow`) remain unresolved.
3. **Dependency pinning** absent in requirements (predictability/reproducibility issue).
4. **Documentation granularity** is high-level and not enough for advanced contributor onboarding.

### Maintainability risk
- Medium-low currently; grows as scope grows unless coverage and standards are tightened.

---

## 5) Productvolwassenheid — 6.0/10

### What is good
- Core product loop exists (device registration/heartbeat, media upload, monitoring, settings/system actions).
- Multiple deployment entry points are provided (scripts, Docker, systemd).

### Gaps blocking 10/10
1. **Governance artifacts** are minimal (no strong release policy, versioning guarantees, quality gates in repo).
2. **Operational excellence criteria** (SLO/SLI, alerting model, support boundaries) are not defined.
3. **Security maturity process** is not fully documented (hardening baseline, secret rotation, threat model cadence).
4. **Product consistency** between docs/planned components and implemented features is incomplete.

### Product maturity risk
- Medium: suitable for evolving internal/early production use, not yet enterprise-grade 10/10 maturity.

---

## Key evidence summary from automated checks

- `pytest`: passed (`2 passed`), but warnings indicate technical debt (deprecated FastAPI startup event usage and UTC naive datetime patterns).
- `bandit`: no medium/high issues, but several low-severity issues including hardcoded-password-pattern detections and subprocess call scrutiny.
- `compileall`: clean.
- `shellcheck`: clean for reviewed scripts.

---

## Final answer to your question

If your bar is truly **10/10 across architecture, security, operations, maintainability, and product maturity**, this codebase is **not there yet**.

It is in a **solid improving state**, but currently sits around:

- Architectuur: **7.5/10**
- Security: **6.5/10**
- Operations: **6.0/10**
- Maintainability: **7.0/10**
- Productvolwassenheid: **6.0/10**

(As requested, this audit does not perform broad remediation.)
