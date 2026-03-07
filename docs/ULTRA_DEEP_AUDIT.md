# Recall Ultra-Deep Code Audit

Date: 2026-03-07
Scope: Entire repository (`/workspace/recall`)

## Methodology

1. Manual review of Python services, shell installers, container assets, and front-end pages.
2. Static sanity checks:
   - `python3 -m compileall -q recall-server recall-player tools`
   - `bandit -q -r recall-server recall-player tools -f txt`
   - `shellcheck install.sh uninstall.sh update.sh recall-install.sh`
3. Targeted pattern hunt for high-risk anti-patterns (`except:`, unbounded upload flows, debug binds, host-wide service exposure).

---

## Executive Summary

The project is functionally compact and easy to reason about, but the default deployment posture is **not production-safe**. The largest risk cluster is around **unauthenticated control/data endpoints** and **unsafe file upload handling**. In addition, installer/runtime scripts use practices that reduce operational reliability and hardening (unquoted vars, broad privileged operations, running services on all interfaces by default).

### Overall risk rating

- **Security:** High
- **Reliability:** Medium
- **Operational maturity:** Low-to-Medium

---

## Findings (Prioritized)

## 1) Unauthenticated API surface allows arbitrary writes and device spoofing
**Severity:** Critical

### Evidence
- FastAPI server exposes `/device/register`, `/devices`, `/monitor`, and `/media/upload` without authn/authz.  
- Device registration writes directly into global state keyed only by caller-controlled `id`.

### Impact
Any host that can reach the service can:
- Overwrite or impersonate device identities.
- Upload arbitrary files into the media directory.
- Harvest host telemetry (`/monitor`) and fleet metadata (`/devices`).

### Recommendation
- Require API key or mTLS at minimum for all non-root routes.
- Add per-endpoint authorization checks.
- Restrict service bind or enforce reverse-proxy auth if LAN-wide exposure is required.

---

## 2) File upload path traversal via unsanitized filename
**Severity:** Critical

### Evidence
- `path = MEDIA_DIR / file.filename` in FastAPI API.
- `path = os.path.join(MEDIA_DIR, file.filename)` in Flask dev server.

### Impact
Attackers can attempt `../../` traversal payloads in multipart filenames and write outside intended media storage (behavior depends on server/framework handling and filesystem permissions). Even partial traversal or overwrite inside media can still be destructive.

### Recommendation
- Normalize with `Path(file.filename).name` (or Werkzeug `secure_filename`) and validate against allowlist.
- Resolve and verify target path remains within `MEDIA_DIR` before writing.
- Generate server-side UUID filenames; store original name only as metadata.

---

## 3) Upload endpoint lacks file-size and file-type limits (DoS/storage abuse)
**Severity:** High

### Evidence
- No max content length or stream limits in FastAPI or Flask upload flows.
- No MIME/type validation before save.

### Impact
Potential disk exhaustion, oversized payload memory pressure, and long-request resource starvation.

### Recommendation
- Enforce request size limits at app and reverse-proxy layers.
- Validate MIME and extension allowlist.
- Add quota controls and cleanup/retention policy.

---

## 4) Dev server shipped with `debug=True` and `0.0.0.0` bind
**Severity:** High (dev-time), Medium (if accidentally exposed)

### Evidence
- `app.run(host="0.0.0.0", port=8080, debug=True)`.

### Impact
If reachable from untrusted network, Werkzeug debugger can expose powerful introspection and (in some configurations) code execution primitives.

### Recommendation
- Default to `debug=False`.
- Bind to `127.0.0.1` for local tooling.
- Gate debug mode via explicit env var.

---

## 5) Broad `except:` blocks suppress operational failure signals
**Severity:** Medium

### Evidence
- `except:` in `get_cpu_temp`, `/monitor` fallback, and player registration loop.

### Impact
Real defects (permission errors, runtime regressions, API drift) are silently hidden, reducing observability and delaying incident response.

### Recommendation
- Catch specific exceptions (`FileNotFoundError`, `requests.RequestException`, etc.).
- Emit structured logs with cause/context.
- Preserve mock mode but include explicit fault markers.

---

## 6) Agent registration HTTP call has no timeout/backoff strategy
**Severity:** Medium

### Evidence
- `requests.post(...)` called without timeout in an infinite loop.

### Impact
Potential thread hangs on network pathologies; noisy retry profile during outages; avoidable resource churn.

### Recommendation
- Add connect/read timeout.
- Implement bounded exponential backoff with jitter.
- Distinguish transient vs permanent failures.

---

## 7) In-memory global `devices` state has concurrency and durability limitations
**Severity:** Medium

### Evidence
- Mutable process-global dict used as source of truth in both API servers.

### Impact
- Lost state on restart.
- Race conditions under multi-worker deployments.
- No TTL/offline semantics except overwrites.

### Recommendation
- Move to persistent store (SQLite/Redis/Postgres).
- Add heartbeat timestamp and expiration logic.
- Add schema validation (Pydantic model) for registration payloads.

---

## 8) Install/update scripts contain portability and safety gaps
**Severity:** Medium

### Evidence
- Unquoted variable expansions in privileged commands.
- Shebang not first line in multiple scripts.
- Runtime dependence on mutable latest packages without pinning.

### Impact
Potential word-splitting bugs, inconsistent installs across environments, fragile automation behavior.

### Recommendation
- Quote all variable expansions.
- Ensure shebang first line.
- Pin minimal dependency ranges and record a lock/constraints file.

---

## 9) Docker assets appear inconsistent with project layout
**Severity:** Medium

### Evidence
- Container command runs `uvicorn server:app` from `/app`, while `server.py` lives under `recall-server/api/`.
- Compose file under `docker/` uses `build: .` and host `./media` volume relative to compose location, which may not align with intended repo root usage.

### Impact
Potential non-working container startup and confusing operator experience.

### Recommendation
- Set `WORKDIR /app/recall-server/api` or command `uvicorn recall-server.api.server:app` with valid module path.
- Reconcile compose paths and document canonical launch command.

---

## 10) Front-end correctness issues indicate low test coverage
**Severity:** Low

### Evidence
- `devices.html` script writes to `#devices`, but no such element exists.
- `monitor.html` duplicates chart/info updates and contains inconsistent temp rendering branches.
- Navigation links include `settings.html`, file absent.
- README says dev server opens at `:5000`, script announces/runs `:8080`.

### Impact
Broken UX, confusion, and avoidable troubleshooting overhead.

### Recommendation
- Add minimal UI smoke tests (Playwright).
- Add CI checks for broken internal links and JS runtime errors.
- Align documentation with runtime defaults.

---

## Static Analysis Output Summary

### Bandit
- High: 1
- Medium: 2
- Low: 8
- Key hits: Flask debug mode, request without timeout, broad exception suppressions.

### ShellCheck
- Errors and infos detected in install/update/uninstall scripts.
- Most important: shebang placement and quoting safety.

---

## 30/60/90 Day Remediation Plan

### 0–30 days (must do)
1. Add authentication for all mutating and telemetry endpoints.
2. Fix upload sanitization and hard path boundary checks.
3. Add request size limits and upload allowlist.
4. Disable debug mode and localize dev bind defaults.

### 31–60 days
1. Replace global dict state with persistent store + schema validation.
2. Add structured logging and exception taxonomy.
3. Harden install scripts (quoting, pinning, idempotency).

### 61–90 days
1. CI pipeline: lint, static security checks, smoke tests.
2. Container hardening and verified compose workflow.
3. Threat model + security baseline document.

---

## Suggested Acceptance Criteria

- Unauthenticated requests to `/device/register` and `/media/upload` return 401/403.
- Upload attempts with traversal filenames are rejected with 400.
- Oversized uploads rejected deterministically.
- Dev server defaults: `debug=False`, bind `127.0.0.1`.
- Player agent registration uses explicit timeout and bounded backoff.
- CI runs compile/lint/security checks on each PR.
