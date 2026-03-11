# Backend Enterprise Layout

This directory is the target backend root for the enterprise rebuild.

## Target structure

- `backend/app/api/routes` -> HTTP request/response only
- `backend/app/services` -> business logic only
- `backend/app/repositories` -> database access/query logic only
- `backend/app/models` -> ORM/domain models
- `backend/app/schemas` -> request/response/data contracts
- `backend/app/core` -> config/auth/security/logging
- `backend/app/db` -> session/engine/migrations wiring
- `backend/app/workers` -> async task modules
- `backend/app/integrations` -> external service adapters
- `backend/app/utils` -> shared helper utilities

## Migration rule set

1. Do not add new business logic to monolithic entrypoint files.
2. New API endpoints must be thin and delegate to services.
3. New SQL/ORM queries must be implemented in repositories.
4. Cross-cutting concerns must be centralized in `core/`.

## Transitional mapping from legacy layout

`backend/app` is the canonical and only supported backend runtime location.

## Namespace note

Python imports in migrated modules should use `backend.app.*` as the canonical package path.
