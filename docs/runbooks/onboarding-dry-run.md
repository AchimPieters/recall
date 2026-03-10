# Runbook: Onboarding Dry-Run

## Purpose
Validate that a new engineer can bootstrap backend + frontend and run baseline checks without tribal knowledge.

## Dry-run checklist
1. Clone repository and inspect top-level structure (`backend/`, `frontend/`, `docs/`).
2. Backend bootstrap:
   - `cd backend`
   - `python -m pip install -r requirements.txt`
   - `pytest -q tests/test_security_headers.py tests/test_backup_restore.py`
3. Frontend bootstrap:
   - `cd frontend`
   - `npm ci`
   - `npm run build`
4. Documentation quality gate:
   - `python tools/doc_lint.py`
5. Confirm app basics in docs:
   - API health endpoint (`/api/v1/health`)
   - observability summary endpoint (`/api/v1/observability/summary`)

## Exit criteria
- All commands pass.
- No missing setup steps encountered.
- Any friction points are captured as follow-up docs issues.
