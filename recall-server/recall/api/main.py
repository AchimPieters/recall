import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from contextlib import asynccontextmanager
from uuid import uuid4
from threading import Lock

import structlog
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, Histogram, generate_latest
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.extension import _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from sqlalchemy import text
from sqlalchemy.orm import Session

from recall.api.routes import (
    devices,
    events,
    media,
    monitor,
    playlists,
    settings,
    system,
)
from recall.core.config import get_settings
from recall.core.security import create_access_token, get_password_hash, verify_password
from recall.db.database import Base, engine, get_db
from recall.models import User
from recall.services.device_service import DeviceService

settings_conf = get_settings()

logging.basicConfig(format="%(message)s", level=logging.INFO)
structlog.configure(processors=[structlog.processors.JSONRenderer()])
logger = structlog.get_logger(service="recall-api")

limiter = Limiter(key_func=get_remote_address)

failed_login_attempts: dict[str, list[datetime]] = {}
failed_login_lock = Lock()


def _prune_failed_attempts(username: str, now: datetime) -> list[datetime]:
    window = timedelta(minutes=settings_conf.auth_lockout_minutes)
    attempts = failed_login_attempts.get(username, [])
    pruned = [attempt for attempt in attempts if now - attempt < window]
    if pruned:
        failed_login_attempts[username] = pruned
    else:
        failed_login_attempts.pop(username, None)
    return pruned


def _is_locked_out(username: str, now: datetime) -> bool:
    with failed_login_lock:
        attempts = _prune_failed_attempts(username, now)
        return len(attempts) >= settings_conf.auth_lockout_threshold


def _record_failed_login(username: str, now: datetime) -> None:
    with failed_login_lock:
        attempts = _prune_failed_attempts(username, now)
        attempts.append(now)
        failed_login_attempts[username] = attempts


def _clear_failed_logins(username: str) -> None:
    with failed_login_lock:
        failed_login_attempts.pop(username, None)


def _bootstrap_admin() -> None:
    db_gen = get_db()
    db = next(db_gen)
    try:
        admin = (
            db.query(User)
            .filter(User.username == settings_conf.bootstrap_admin_username)
            .first()
        )
        password = settings_conf.bootstrap_admin_password.strip()
        if admin or not password:
            return

        db.add(
            User(
                username=settings_conf.bootstrap_admin_username,
                password_hash=get_password_hash(password),
                role="admin",
            )
        )
        db.commit()
        logger.info("bootstrap_admin", status="created")
    finally:
        db_gen.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings_conf.auto_create_schema:
        Base.metadata.create_all(bind=engine)
    _bootstrap_admin()
    logger.info("startup", action="bootstrap", status="ok")
    yield


app = FastAPI(title=settings_conf.app_name, lifespan=lifespan)
app.state.limiter = limiter
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

app.include_router(devices.router)
app.include_router(media.router)
app.include_router(events.router)
app.include_router(monitor.router)
app.include_router(settings.router)
app.include_router(playlists.router)
app.include_router(system.router)

device_count = Gauge("device_count", "Total devices")
device_online = Gauge("device_online", "Online devices")
request_latency = Histogram(
    "http_request_duration_seconds", "Request latency", ["method", "path"]
)


@app.middleware("http")
async def request_logger(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", uuid4().hex)
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


@app.get("/")
def root():
    return {"status": "recall running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/live")
def live():
    return {"status": "live"}


@app.get("/version")
def version():
    return {
        "version": settings_conf.app_version,
        "environment": settings_conf.environment,
    }


@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ready"}


@app.post("/token")
@limiter.limit("10/minute")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    username = form_data.username.strip()

    if _is_locked_out(username, now):
        raise HTTPException(status_code=429, detail="Account temporarily locked")

    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        _record_failed_login(username, now)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    _clear_failed_logins(username)
    token = create_access_token(subject=user.username, role=user.role)
    return {"access_token": token, "token_type": "Bearer"}


@app.get("/devices")
def devices_summary(db: Session = Depends(get_db)):
    svc = DeviceService(db)
    svc.mark_presence()
    devices_list = svc.list_devices()
    device_count.set(len(devices_list))
    device_online.set(len([d for d in devices_list if d.status == "online"]))
    return devices_list


@app.get("/metrics")
def metrics():
    return PlainTextResponse(
        generate_latest().decode("utf-8"), media_type=CONTENT_TYPE_LATEST
    )
