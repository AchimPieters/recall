# Deployment

Use `docker/docker-compose.yml` for local stacks with API + PostgreSQL + Redis.

## Required environment configuration
- Set a strong `JWT_SECRET` before starting the API.
- Optionally set `RECALL_BOOTSTRAP_ADMIN_PASSWORD` once to create an initial admin user.
- Restrict browser origins with `RECALL_CORS_ORIGINS` (comma-separated URLs).

Container targets:
- recall-api
- recall-worker
- recall-postgres
- recall-redis
- recall-frontend

## TLS and secret management
- Set `RECALL_ENFORCE_HTTPS=true` in production and terminate TLS at ingress/load balancer.
- Configure `JWT_SECRETS` as a comma-separated key-ring to support rotation; first value is used for signing.
- Keep `JWT_SECRET`/`JWT_SECRETS` in a secret manager, never in git.

## Agent defaults
- `recall-player/agent.py` defaults to `https://localhost:8000` and TLS verification enabled.
- Prefer `RECALL_ACCESS_TOKEN` for agent authentication.
- API-key-only mode is intentionally opt-in (`RECALL_AGENT_ALLOW_API_KEY=true`) for legacy setups.


## Kubernetes
- `k8s/api-deployment.yaml`
- `k8s/worker-deployment.yaml`
- `k8s/frontend-deployment.yaml`
