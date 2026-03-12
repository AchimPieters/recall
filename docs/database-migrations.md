# Database Migration Policy

## Policy
- Runtime application code must **never** mutate schema (no `Base.metadata.create_all`, no runtime `ALTER TABLE`).
- Schema changes are applied only through versioned migrations:
  - SQL source-of-truth files in `backend/app/db/migrations/`.
  - Alembic revisions in `backend/alembic/versions/` that orchestrate migration application.
- CI/CD and explicit migration jobs execute migrations through the migration layer; API runtime never applies schema DDL during startup.

## Workflow
1. Add a new ordered SQL migration file `NNNN_description.sql` in `backend/app/db/migrations/`.
2. Add/update the Alembic revision in `backend/alembic/versions/` when migration orchestration changes.
3. Validate migrations on SQLite (tests) and PostgreSQL (staging/production).
4. Deploy code + migration together.
5. Never edit an already-applied migration in-place.

## Execution
- Run migrations explicitly before API rollout: `PYTHONPATH=. python -m backend.app.db.migrate_cli` (run from repo root)
- Alembic orchestration entrypoint: `cd backend && alembic upgrade head`

## Verification
- `rg "Base\.metadata\.create_all|ALTER TABLE" backend/app`
- `cd backend && alembic upgrade head`
- Ensure `schema_migrations` contains all expected SQL migration versions.
