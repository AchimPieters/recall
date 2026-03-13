# Secrets Management

## Policy
- Secrets are managed through Kubernetes `Secret` resources and injected as environment variables.
- `.env` files are development-only and must not be source-of-truth for production secrets.
- JWT signing supports key-rings through `JWT_SECRETS` with newest key first.

## Kubernetes integration
- Baseline example is in `k8s/namespace-and-secrets.example.yaml`.
- Recommended runtime variables:
  - `JWT_SECRETS`
  - `RECALL_JWT_SECRET_LAST_ROTATED_AT`
  - `DATABASE_URL`
  - `REDIS_URL`

## Rotation policy
- Rotate JWT signing keys every `RECALL_SECRET_ROTATION_MAX_AGE_DAYS` (default `30`).
- Keep previous key in `JWT_SECRETS` during grace period for token validation.
- After token TTL expiry, remove deprecated keys.

## Rotation scheduler
- Worker task `recall.workers.evaluate_secret_rotation` evaluates if rotation is due.
- Result payload includes `rotation_due`, `max_age_days`, and `last_rotated_at`.

## Runtime enforcement
- Outside development (`RECALL_ENV != dev`) the backend now **requires** `JWT_SECRETS` (key-ring from Kubernetes Secret).
- The first value in `JWT_SECRETS` is used as active signing key; remaining keys are accepted for verification during rotation windows.
- `RECALL_CLAMAV_FAIL_OPEN=true` is rejected outside development.

## Verification
- `cd backend && pytest -q tests/test_secret_management_policy.py`
