# Developer Onboarding

## 1) Repository structure
- `backend/app/`: API routes, services, repositories, models, workers, core infrastructure.
- `backend/tests/`: backend unit/integration and architecture boundary tests.
- `frontend/`: React + TypeScript web app (Vite, ESLint, Prettier, Vitest).
- `agent/`: edge/player agent runtime and tests.
- `docs/`: architecture, runbooks, security, deployment and governance policies.

## 2) Local setup
### Backend
1. `python -m pip install --upgrade pip`
2. `pip install -r backend/requirements.txt`
3. Start API: `uvicorn backend.app.api.main:app --reload --port 8000`

### Frontend
1. `cd frontend`
2. `npm ci`
3. Start dev server: `npm run dev`

## 3) Debug flows
- API startup and request logs are emitted via structured logging in `backend/app/api/main.py`.
- Worker status can be inspected through worker visibility endpoints and celery inspect snapshots.
- Device issues: validate register/heartbeat/config/command flows with route tests in `backend/tests/`.
- Upload issues: use media pipeline tests to isolate MIME/container/structure validation behavior.

## 4) Test strategy
### Backend checks
- Fast regression subset:
  - `pytest -q backend/tests/test_auth_enterprise.py`
  - `pytest -q backend/tests/test_device_provisioning.py`
  - `pytest -q backend/tests/test_media_pipeline.py`
  - `pytest -q backend/tests/test_architecture_boundaries.py`

### Frontend checks
- `cd frontend && npm run format:check`
- `cd frontend && npm run lint`
- `cd frontend && npm run test`
- `cd frontend && npm run build`

### CI gates
- Coverage workflow for backend + agent.
- Supply-chain workflow (Syft + Grype + Cosign).
- Environment promotion workflow (`dev -> staging -> production`).
