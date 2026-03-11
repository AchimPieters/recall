# Database Migration Policy

## Policy
- Runtime application code must **never** mutate schema (no `Base.metadata.create_all`, no runtime `ALTER TABLE`).
- Schema changes are applied only through versioned SQL migrations in `backend/app/db/migrations/`.
- CI/CD and startup flows execute migrations through `backend.app.db.migrate.apply_sql_migrations`.

## Workflow
1. Add a new ordered migration file `NNNN_description.sql`.
2. Validate migration on SQLite (tests) and PostgreSQL (staging/production).
3. Deploy code + migration together.
4. Never edit an already-applied migration in-place.

## Verification
- `rg "Base\.metadata\.create_all|ALTER TABLE" backend/app`
- Ensure results only contain migration SQL files.
