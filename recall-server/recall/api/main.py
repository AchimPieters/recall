import logging
from pathlib import Path
from contextlib import asynccontextmanager

import structlog
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.extension import _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from sqlalchemy import text
from sqlalchemy.orm import Session

from recall.api.routes import devices, media, monitor, settings, system
from recall.core.config import get_settings
from recall.core.security import create_access_token, verify_password, get_password_hash
from recall.db.database import Base, engine, get_db
from recall.models import User
from recall.services.device_service import DeviceService

settings_conf = get_settings()

logging.basicConfig(format="%(message)s", level=logging.INFO)
structlog.configure(processors=[structlog.processors.JSONRenderer()])
logger = structlog.get_logger(service="recall-api")

limiter = Limiter(key_func=get_remote_address)


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
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
app.include_router(monitor.router)
app.include_router(settings.router)
app.include_router(system.router)

device_count = Gauge("device_count", "Total devices")
device_online = Gauge("device_online", "Online devices")


@app.middleware("http")
async def request_logger(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    logger.info(
        "request",
        action=f"{request.method} {request.url.path}",
        status=response.status_code,
    )
    return response


@app.get("/")
def root():
    return {"status": "recall running"}


@app.get("/health")
def health():
    return {"status": "ok"}


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
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
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
