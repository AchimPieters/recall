# Development

## Install
```bash
pip install -r backend/requirements.txt
```

## Run API
```bash
uvicorn backend.app.api.main:app --reload --port 8000
```

## Database migrations
See `docs/database-migrations.md` for migration policy and execution flow.
