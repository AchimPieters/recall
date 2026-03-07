# Recall

Production-oriented digital signage platform.

## Components
- `recall-server/recall/api`: FastAPI application and route layer.
- `recall-server/recall/services`: business logic.
- `recall-server/recall/models`: SQLAlchemy ORM models.
- `recall-server/recall/db`: database configuration and migrations.
- `recall-server/recall/workers`: background tasks.

## Quick start
```bash
pip install -r recall-server/requirements.txt
cd recall-server
uvicorn recall.api.main:app --host 0.0.0.0 --port 8000
```

## Docker
```bash
./install-docker.sh
```

## Documentation
See `docs/` for architecture, API, protocol, deployment, and development docs.
