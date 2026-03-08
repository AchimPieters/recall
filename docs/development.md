# Development

## Install
```bash
pip install -r recall-server/requirements.txt
```

## Run API
```bash
cd recall-server
uvicorn recall.api.main:app --reload --port 8000
```


## Database migrations (Alembic)
```bash
cd recall-server
alembic upgrade head

# create a new migration
alembic revision -m "describe change"
```

Legacy SQL snapshots remain under `recall/db/migrations/` for historical traceability.
