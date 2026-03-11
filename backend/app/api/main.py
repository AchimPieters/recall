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
from backend.app.core.tracing import init_tracing
from backend.app.db.database import engine, get_db
from backend.app.db.migrate import apply_sql_migrations

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


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings_conf.auto_create_schema:
        apply_sql_migrations(engine)
    tracing_enabled = init_tracing("recall-api")
    logger.info("tracing", enabled=tracing_enabled)
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

api_prefix = "/api/v1"
app.include_router(platform.router, prefix=api_prefix)
app.include_router(auth.router, prefix=api_prefix)
app.include_router(devices.router, prefix=api_prefix)
app.include_router(media.router, prefix=api_prefix)
app.include_router(events.router, prefix=api_prefix)
app.include_router(monitor.router, prefix=api_prefix)
app.include_router(settings.router, prefix=api_prefix)
app.include_router(playlists.router, prefix=api_prefix)
app.include_router(security.router, prefix=api_prefix)
app.include_router(system.router, prefix=api_prefix)

request_latency = Histogram(
    "http_request_duration_seconds", "Request latency", ["method", "path"]
)


@app.middleware("http")
async def request_logger(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", uuid4().hex)

    host_header = request.headers.get("host", "")
    host = host_header.split(":", 1)[0].strip().lower()
    allowed_hosts = set(settings_conf.allowed_hosts)
    if host and "*" not in allowed_hosts and host not in allowed_hosts:
        return PlainTextResponse("Invalid host header", status_code=400)

    if settings_conf.enforce_https and settings_conf.environment != "dev":
        forwarded_proto = request.headers.get("X-Forwarded-Proto", "http")
        scheme = request.url.scheme
        if settings_conf.trust_forwarded_proto:
            scheme = forwarded_proto
        if scheme != "https":
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
    if settings_conf.enforce_https and settings_conf.environment != "dev":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    logger.info(
        "request",
        request_id=request_id,
        action=f"{request.method} {request.url.path}",
        latency_ms=round(elapsed * 1000, 2),
        status=response.status_code,
    )
    return response


failed_login_attempts = auth.failed_login_attempts
