# API Versioning

## Versioning Strategy
- All private API endpoints are served under `/api/v1/*`.
- Public API endpoints are served under `/api/public/v1/*`.
- New breaking changes require a new major prefix (for example `/api/v2/*`).
- Backward-compatible additions remain in `v1`.

## Routing Rule
- FastAPI routers are mounted with `prefix="/api/v1"` in `backend/app/api/main.py`.
- Public API router is mounted with `prefix="/api/public/v1"`.
- Frontend API clients must call versioned endpoints only.

## Deprecation Rule
- Deprecate endpoints with a published timeline.
- Maintain old major versions only for the defined support window.
