import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import Histogram
from slowapi.errors import RateLimitExceeded
from slowapi.extension import _rate_limit_exceeded_handler
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError

from backend.app.api.routes import (
    auth,
    devices,
    events,
    media,
    monitor,
    platform,
    playlists,
    security,
    settings,
    system,
)
from backend.app.core.config import get_settings
from backend.app.db.database import Base, engine, get_db

settings_conf = get_settings()

logging.basicConfig(format="%(message)s", level=logging.INFO)
structlog.configure(processors=[structlog.processors.JSONRenderer()])
logger = structlog.get_logger(service="recall-api")


def _bootstrap_admin() -> None:
    db_gen = get_db()
    db = next(db_gen)
    try:
        auth.bootstrap_admin(db)
        logger.info("bootstrap_admin", status="ready")
    finally:
        db_gen.close()


def _ensure_runtime_schema_compat() -> None:
    with engine.begin() as conn:
        statements = [
            "ALTER TABLE events ADD COLUMN organization_id INTEGER",
            "ALTER TABLE alerts ADD COLUMN organization_id INTEGER",
            "ALTER TABLE device_screenshots ADD COLUMN organization_id INTEGER",
            "ALTER TABLE device_groups ADD COLUMN organization_id INTEGER",
        ]
        for statement in statements:
            try:
                conn.execute(text(statement))
            except (OperationalError, ProgrammingError):
                pass


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings_conf.auto_create_schema:
        Base.metadata.create_all(bind=engine)
        _ensure_runtime_schema_compat()
    _bootstrap_admin()
    logger.info("startup", action="bootstrap", status="ok")
    yield


app = FastAPI(title=settings_conf.app_name, lifespan=lifespan)
app.state.limiter = auth.limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings_conf.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

WEB_DIR = Path(__file__).resolve().parents[2] / "web"
if WEB_DIR.exists():
    app.mount("/web", StaticFiles(directory=str(WEB_DIR), html=True), name="web")

for prefix in ("", "/api/v1"):
    app.include_router(platform.router, prefix=prefix)
    app.include_router(auth.router, prefix=prefix)
    app.include_router(devices.router, prefix=prefix)
    app.include_router(media.router, prefix=prefix)
    app.include_router(events.router, prefix=prefix)
    app.include_router(monitor.router, prefix=prefix)
    app.include_router(settings.router, prefix=prefix)
    app.include_router(playlists.router, prefix=prefix)
    app.include_router(security.router, prefix=prefix)
    app.include_router(system.router, prefix=prefix)

request_latency = Histogram(
    "http_request_duration_seconds", "Request latency", ["method", "path"]
)


@app.middleware("http")
async def request_logger(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", uuid4().hex)
    if settings_conf.enforce_https and settings_conf.environment != "dev":
        forwarded_proto = request.headers.get("X-Forwarded-Proto", "http")
        if forwarded_proto != "https" and request.url.scheme != "https":
            return PlainTextResponse("HTTPS required", status_code=426)

    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start

    request_latency.labels(request.method, request.url.path).observe(elapsed)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    logger.info(
        "request",
        request_id=request_id,
        action=f"{request.method} {request.url.path}",
        latency_ms=round(elapsed * 1000, 2),
        status=response.status_code,
    )
    return response


failed_login_attempts = auth.failed_login_attempts
