# Recall

Recall is a production-oriented digital signage platform with an enterprise migration path toward a modular, secure, multi-tenant architecture.

## Architecture at a glance
- **API/backend**: FastAPI + service/repository layering.
- **Persistence**: PostgreSQL + SQLAlchemy + migrations.
- **Async workloads**: Celery + Redis.
- **Device layer**: agent heartbeat, playback, metrics and remote operations.
- **Observability**: Prometheus/Grafana/Loki target stack.

See the detailed architecture blueprint in [`docs/architecture.md`](docs/architecture.md).

## Repository overview
- `backend/`: canonical backend runtime.
- `agent/`: device agent runtime.
- `frontend/`: web frontend.
- `docker/`: local container build and compose stack.
- `docs/`: architecture, API, security, deployment and runbooks.

## Development quick start
```bash
python -m pip install -r backend/requirements.txt
uvicorn backend.app.api.main:app --host 0.0.0.0 --port 8000
```

## Testing and quality
```bash
pytest -q backend
pytest -q agent/tests
```

## Docker compose stack
`docker/docker-compose.yml` contains:
- `recall-api`
- `recall-worker`
- `recall-agent`
- `recall-frontend`
- `postgres`
- `redis`

## Deployment
- Local/container install helpers: `install-docker.sh`, `install-pi.sh`, `install-x86.sh`.
- See [`docs/deployment.md`](docs/deployment.md) for deployment guidance.

## Security
- Responsible disclosure policy: [`SECURITY.md`](SECURITY.md).
- Security architecture and controls: [`docs/security.md`](docs/security.md).
