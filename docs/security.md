# Security Architecture

## Authentication and authorization
- OAuth2 password/login flow with JWT access tokens.
- Refresh token rotation.
- RBAC roles: admin, operator, viewer, device.

## Defensive controls
- Rate limiting on auth and public endpoints.
- Account lockout after repeated failed logins.
- Strict tenant scoping in repositories.
- Audit logging for critical actions.

## Upload security
- MIME allow-list and max file size limits.
- UUID-based storage names.
- Antivirus scanning (ClamAV).
- Rejection of corrupt/duplicate payloads.

## Transport and headers
- TLS termination at reverse proxy.
- HSTS, CSP, X-Frame-Options, X-Content-Type-Options.

## CI security gates
- bandit, dependency scanning, pinned tooling.
