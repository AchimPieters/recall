# Changelog

## Unreleased

## v2.0.0 - 2026-03-13
- Hardened agent edge reliability with atomic media downloads and offline fallback path preservation.
- Tightened release sign-off governance with strict version/date/approver validation in CI.
- Added release governance artifacts and regression coverage for acceptance/release gates.

## v1.1.0 - 2026-03-13
- Added DR runbook and Kubernetes CronJob examples for DB/media backups and restore drills.
- Added combined backend+agent coverage gate at 85% and expanded backend tests for system/display/worker/tracing paths.
- Updated enterprise phase audit with current operations and maintainability status.

## v1.0.0 - 2026-03-13
- Consolidated backend runtime and standardized API versioning on `/api/v1`.
- Added enterprise auth/security building blocks (MFA flows, audit hardening, public API key governance).
- Added release and supply-chain gates with changelog policy, SBOM scanning, and signing workflow.

- Added organization-scoped access controls for device/media/events/alerts endpoints and persisted organization context on new records.
- Added runtime schema compatibility upgrades for organization-scoped columns and a dedicated migration (`0003_multi_tenant_isolation.sql`).
- Expanded CI quality gates with ruff, black, mypy, bandit (high severity), and dependency audit.
- Added tenant-isolation test coverage to prevent cross-organization device visibility.
- Hardened refresh token expiry comparison to use timezone-aware UTC datetimes.
- Tightened player agent defaults to block insecure HTTP/TLS mismatches and require token-first auth unless API-key fallback is explicitly enabled.
- Expanded deployment/operations docs with agent auth guidance, dashboard/tracing expectations, and secret-rotation practices.
- Added account lockout controls for repeated failed logins and configurable lockout settings.
- Added `/version` endpoint for runtime version/environment introspection.
- Added audit gap closure document and tests for lockout/version behavior.
- Added playlist and scheduling API endpoints plus device config playlist resolution.
- Added audit remediation document that maps architecture/security/ops/maintainability/product points to implementation.
- Added tests for playlist scheduling and config resolution.
- Refactored API into layered architecture.
- Added SQLAlchemy models and database migration baseline.
- Added JWT auth, RBAC, metrics endpoint, and CI pipeline.
