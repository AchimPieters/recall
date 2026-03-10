# Coverage Baseline and Execution Matrix

## Purpose
Provide a repeatable baseline for line coverage reporting while the full enterprise test strategy is being completed.

## Baseline gates
- Backend coverage gate: `--cov-fail-under=60` on `backend/app`.
- Agent coverage gate: `--cov-fail-under=60` on `agent`.
- XML artifacts generated for both domains (`coverage-backend.xml`, `coverage-agent.xml`).

## Local commands
```bash
pytest -q backend/tests --cov=backend/app --cov-report=term-missing --cov-report=xml:coverage-backend.xml --cov-fail-under=60
pytest -q agent/tests --cov=agent --cov-report=term-missing --cov-report=xml:coverage-agent.xml --cov-fail-under=60
```

## CI integration
Coverage execution is automated in `.github/workflows/coverage-ci.yml` and uploads XML artifacts for review.

## Next increments
- Raise fail-under thresholds by domain after closing low-covered modules.
- Add per-module thresholds for critical paths (auth, settings, device protocol, media pipeline).
- Add trend reporting in PR comments.


## Per-module thresholds (current baseline)
- Backend:
  - `api/routes/auth.py >= 70%`
  - `services/device_service.py >= 75%`
  - `services/media_service.py >= 60%`
  - `services/settings_service.py >= 70%`
- Agent:
  - `agent.py >= 40%`
  - `agent_modules/recovery.py >= 80%`

Thresholds are enforced in CI with `tools/coverage_threshold_check.py` over the generated XML reports.
