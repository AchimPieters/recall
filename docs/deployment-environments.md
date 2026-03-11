# Deployment Environments and Promotion Flow

## Environments
- `dev`: continuous integration and rapid validation.
- `staging`: pre-production validation, smoke tests, backup/restore verification.
- `production`: customer-facing environment with protected promotion.

## Promotion path
`dev -> staging -> production`

The GitHub Actions workflow `.github/workflows/environment-promotion.yml` enforces linear promotion:
1. Deploy to `dev`.
2. Run staging smoke checks and deploy to `staging`.
3. Promote to `production` only after staging succeeds.

## Required controls
- Enable GitHub environment protection rules for `staging` and `production`.
- Keep deployment secrets scoped per environment.
- Use immutable image tags (`image_tag`) per promotion run.

## Validation commands (local/CI)
- `pytest -q backend/tests/test_release_gate_check.py backend/tests/test_backup_restore.py`
- `python tools/release_gate_check.py v1.2.0`
