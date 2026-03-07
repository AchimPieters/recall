# Deployment

Use `docker/docker-compose.yml` for local stacks with API + PostgreSQL + Redis.

## Required environment configuration
- Set a strong `JWT_SECRET` before starting the API.
- Optionally set `RECALL_BOOTSTRAP_ADMIN_PASSWORD` once to create an initial admin user.
- Restrict browser origins with `RECALL_CORS_ORIGINS` (comma-separated URLs).

Container targets:
- recall-api
- recall-worker (planned)
- recall-web (planned)
- recall-agent (planned)
