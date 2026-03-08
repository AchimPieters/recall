# Changelog

## Unreleased
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
