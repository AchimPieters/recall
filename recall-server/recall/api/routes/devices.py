from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from recall.core.auth import require_role
from recall.db.database import get_db
from recall.services.device_service import DeviceService

router = APIRouter(prefix="/device", tags=["devices"])


class RegisterPayload(BaseModel):
    id: str
    name: str = "Unnamed"
    version: str | None = None


class HeartbeatPayload(BaseModel):
    id: str
    metrics: dict | None = None


class LogPayload(BaseModel):
    id: str
    level: str = "info"
    action: str = "log"
    message: str


@router.post(
    "/register", dependencies=[Depends(require_role("device", "admin", "operator"))]
)
def register(payload: RegisterPayload, request: Request, db: Session = Depends(get_db)):
    svc = DeviceService(db)
    device = svc.register(
        payload.id,
        payload.name,
        request.client.host if request.client else None,
        payload.version,
    )
    return {"id": device.id, "status": device.status, "last_seen": device.last_seen}


@router.post(
    "/heartbeat", dependencies=[Depends(require_role("device", "admin", "operator"))]
)
def heartbeat(payload: HeartbeatPayload, db: Session = Depends(get_db)):
    svc = DeviceService(db)
    device = svc.heartbeat(payload.id, payload.metrics)
    if not device:
        raise HTTPException(404, "device not found")
    return {"status": device.status, "last_seen": device.last_seen}


@router.get(
    "/config", dependencies=[Depends(require_role("device", "admin", "operator"))]
)
def get_config(device_id: str, db: Session = Depends(get_db)):
    return DeviceService(db).get_config(device_id)


@router.post(
    "/logs", dependencies=[Depends(require_role("device", "admin", "operator"))]
)
def post_logs(payload: LogPayload, db: Session = Depends(get_db)):
    log = DeviceService(db).add_log(
        payload.id, payload.level, payload.action, payload.message
    )
    return {"id": log.id, "timestamp": log.timestamp}


@router.post(
    "/screenshot", dependencies=[Depends(require_role("device", "admin", "operator"))]
)
def post_screenshot():
    return {"accepted": True}


@router.post(
    "/metrics", dependencies=[Depends(require_role("device", "admin", "operator"))]
)
def post_metrics(payload: HeartbeatPayload, db: Session = Depends(get_db)):
    device = DeviceService(db).heartbeat(payload.id, payload.metrics)
    if not device:
        raise HTTPException(404, "device not found")
    return {"status": "recorded"}


@router.get(
    "/list", dependencies=[Depends(require_role("admin", "operator", "viewer"))]
)
def list_devices(db: Session = Depends(get_db)):
    svc = DeviceService(db)
    svc.mark_presence()
    return svc.list_devices()
