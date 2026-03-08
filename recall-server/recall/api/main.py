import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4

import structlog
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, Histogram, generate_latest
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.extension import _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from recall.api.routes import (
    devices,
    events,
    media,
    monitor,
    playlists,
    security,
    settings,
    system,
)
from recall.core.config import get_settings
from recall.core.auth import AuthUser, get_current_user, require_role
from recall.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    hash_token,
    parse_refresh_token,
    verify_password,
)
from recall.db.database import Base, engine, get_db
from recall.models import User
from recall.repositories.security_repository import SecurityRepository
from recall.services.device_service import DeviceService

settings_conf = get_settings()

logging.basicConfig(format="%(message)s", level=logging.INFO)
structlog.configure(processors=[structlog.processors.JSONRenderer()])
logger = structlog.get_logger(service="recall-api")

limiter = Limiter(key_func=get_remote_address)

failed_login_attempts: dict[str, list[datetime]] = {}
failed_login_lock = Lock()


class RefreshPayload(BaseModel):
    refresh_token: str


def _utc_normalized(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


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
                # Column likely already exists (or DB engine has equivalent schema).
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

for prefix in ("", "/api/v1"):
    app.include_router(devices.router, prefix=prefix)
    app.include_router(media.router, prefix=prefix)
    app.include_router(events.router, prefix=prefix)
    app.include_router(monitor.router, prefix=prefix)
    app.include_router(settings.router, prefix=prefix)
    app.include_router(playlists.router, prefix=prefix)
    app.include_router(security.router, prefix=prefix)
    app.include_router(system.router, prefix=prefix)

device_count = Gauge("device_count", "Total devices")
device_online = Gauge("device_online", "Online devices")
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
        "api_versions": ["v1"],
    }


@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ready"}


@app.post("/token")
@app.post("/auth/login")
@limiter.limit("10/minute")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    username = form_data.username.strip()
    sec_repo = SecurityRepository(db)

    if _is_locked_out(username, now):
        sec_repo.add_security_event(
            actor=username,
            event_type="login_locked",
            detail="Account temporarily locked",
            ip_address=request.client.host if request.client else None,
        )
        raise HTTPException(status_code=429, detail="Account temporarily locked")

    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        _record_failed_login(username, now)
        sec_repo.add_security_event(
            actor=username,
            event_type="login_failed",
            detail="Invalid credentials",
            ip_address=request.client.host if request.client else None,
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")

    _clear_failed_logins(username)
    token = create_access_token(subject=user.username, role=user.role)
    refresh_token, jti = create_refresh_token(subject=user.username)
    refresh_exp = now + timedelta(minutes=settings_conf.refresh_token_expire_minutes)
    sec_repo.create_refresh_token(user.username, hash_token(jti), refresh_exp)
    sec_repo.add_security_event(
        actor=username,
        event_type="login_success",
        detail="Access and refresh token issued",
        ip_address=request.client.host if request.client else None,
    )
    return {
        "access_token": token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
    }


@app.post("/token/refresh")
@app.post("/auth/refresh")
def refresh_token(
    payload: RefreshPayload,
    request: Request,
    db: Session = Depends(get_db),
):
    sec_repo = SecurityRepository(db)
    client_ip = request.client.host if request.client else None
    try:
        subject, jti = parse_refresh_token(payload.refresh_token)
    except Exception as exc:  # noqa: BLE001
        sec_repo.add_security_event(
            actor="unknown",
            event_type="token_refresh_failed",
            detail="Malformed refresh token",
            ip_address=client_ip,
        )
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc

    token_record = sec_repo.get_active_refresh_token(hash_token(jti))
    if not token_record or _utc_normalized(token_record.expires_at) < datetime.now(
        timezone.utc
    ):
        sec_repo.add_security_event(
            actor=subject,
            event_type="token_refresh_failed",
            detail="Refresh token expired or revoked",
            ip_address=client_ip,
        )
        raise HTTPException(status_code=401, detail="Refresh token expired or revoked")

    user = db.query(User).filter(User.username == subject).first()
    if not user:
        sec_repo.add_security_event(
            actor=subject,
            event_type="token_refresh_failed",
            detail="Unknown user",
            ip_address=client_ip,
        )
        raise HTTPException(status_code=401, detail="Unknown user")

    sec_repo.revoke_refresh_token(hash_token(jti))
    new_refresh, new_jti = create_refresh_token(subject=user.username)
    new_expiry = datetime.now(timezone.utc) + timedelta(
        minutes=settings_conf.refresh_token_expire_minutes
    )
    sec_repo.create_refresh_token(user.username, hash_token(new_jti), new_expiry)
    sec_repo.add_security_event(
        actor=user.username,
        event_type="token_refresh",
        detail="Refresh token rotated",
        ip_address=client_ip,
    )
    return {
        "access_token": create_access_token(subject=user.username, role=user.role),
        "refresh_token": new_refresh,
        "token_type": "Bearer",
    }


@app.get("/audit-logs", dependencies=[Depends(require_role("admin"))])
def audit_logs(
    limit: int = 100,
    actor: str | None = None,
    event_type: str | None = None,
    db: Session = Depends(get_db),
):
    rows = SecurityRepository(db).list_security_events(
        limit=max(1, min(limit, 500)), actor=actor, event_type=event_type
    )
    return [
        {
            "id": row.id,
            "actor": row.actor,
            "event_type": row.event_type,
            "detail": row.detail,
            "ip_address": row.ip_address,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@app.get("/devices")
def devices_summary(
    db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)
):
    svc = DeviceService(db)
    svc.mark_presence(organization_id=user.organization_id)
    devices_list = svc.list_devices(organization_id=user.organization_id)
    device_count.set(len(devices_list))
    device_online.set(len([d for d in devices_list if d.status == "online"]))
    return devices_list


@app.get("/metrics")
def metrics():
    return PlainTextResponse(
        generate_latest().decode("utf-8"), media_type=CONTENT_TYPE_LATEST
    )
