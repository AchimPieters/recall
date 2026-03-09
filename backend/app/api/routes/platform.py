from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.core.auth import AuthUser, get_current_user
from backend.app.core.config import get_settings
from backend.app.db.database import get_db
from backend.app.services.device_service import DeviceService

router = APIRouter(tags=["platform"])
settings_conf = get_settings()

device_count = Gauge("device_count", "Total devices")
device_online = Gauge("device_online", "Online devices")


@router.get("/")
def root():
    return {"status": "recall running"}


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/live")
def live():
    return {"status": "live"}


@router.get("/version")
def version():
    return {
        "version": settings_conf.app_version,
        "environment": settings_conf.environment,
        "api_versions": ["v1"],
    }


@router.get("/ready")
def ready(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ready"}


@router.get("/devices")
def devices_summary(
    db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)
):
    svc = DeviceService(db)
    svc.mark_presence(organization_id=user.organization_id)
    devices_list = svc.list_devices(organization_id=user.organization_id)
    device_count.set(len(devices_list))
    device_online.set(len([d for d in devices_list if d.status == "online"]))
    return devices_list


@router.get("/metrics")
def metrics():
    return PlainTextResponse(
        generate_latest().decode("utf-8"), media_type=CONTENT_TYPE_LATEST
    )
