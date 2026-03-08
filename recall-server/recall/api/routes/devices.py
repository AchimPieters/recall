from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from recall.core.auth import (
    AuthUser,
    ensure_organization_access,
    get_current_user,
    require_permission,
    require_role,
)
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


class GroupPayload(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class GroupMemberPayload(BaseModel):
    device_id: str = Field(min_length=1, max_length=64)


class ScreenshotPayload(BaseModel):
    id: str
    image_path: str = Field(min_length=1, max_length=1024)


@router.post(
    "/register", dependencies=[Depends(require_role("device", "admin", "operator"))]
)
def register(
    payload: RegisterPayload,
    request: Request,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    svc = DeviceService(db)
    device = svc.register(
        payload.id,
        payload.name,
        request.client.host if request.client else None,
        payload.version,
        user.organization_id,
    )
    ensure_organization_access(user, device.organization_id)
    return {"id": device.id, "status": device.status, "last_seen": device.last_seen}


@router.post(
    "/heartbeat", dependencies=[Depends(require_role("device", "admin", "operator"))]
)
def heartbeat(
    payload: HeartbeatPayload,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    svc = DeviceService(db)
    device = svc.heartbeat(payload.id, payload.metrics)
    if not device:
        raise HTTPException(404, "device not found")
    ensure_organization_access(user, device.organization_id)
    return {"status": device.status, "last_seen": device.last_seen}


@router.get(
    "/config", dependencies=[Depends(require_role("device", "admin", "operator"))]
)
def get_config(
    device_id: str,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    svc = DeviceService(db)
    if user.organization_id is not None:
        device = svc.get_device(device_id)
        if not device or device.organization_id != user.organization_id:
            raise HTTPException(404, "device not found")
    return svc.get_config(device_id)


@router.post(
    "/logs", dependencies=[Depends(require_role("device", "admin", "operator"))]
)
def post_logs(
    payload: LogPayload,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    log = DeviceService(db).add_log(
        payload.id, payload.level, payload.action, payload.message
    )
    return {"id": log.id, "timestamp": log.timestamp}


@router.get("/logs", dependencies=[Depends(require_permission("devices:read"))])
def list_logs(
    limit: int = 100,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    logs = DeviceService(db).list_logs(
        limit=limit, organization_id=user.organization_id
    )
    return [
        {
            "id": log.id,
            "device_id": log.device_id,
            "level": log.level,
            "action": log.action,
            "message": log.message,
            "timestamp": log.timestamp,
        }
        for log in logs
    ]


@router.post(
    "/screenshot", dependencies=[Depends(require_role("device", "admin", "operator"))]
)
def post_screenshot(
    payload: ScreenshotPayload,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    shot = DeviceService(db).record_screenshot(
        payload.id, payload.image_path, user.organization_id
    )
    return {"accepted": True, "id": shot.id, "captured_at": shot.captured_at}


@router.get("/screenshots", dependencies=[Depends(require_permission("devices:read"))])
def get_screenshots(
    device_id: str | None = None,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    return [
        {
            "id": shot.id,
            "device_id": shot.device_id,
            "image_path": shot.image_path,
            "captured_at": shot.captured_at,
        }
        for shot in DeviceService(db).list_screenshots(
            device_id=device_id, organization_id=user.organization_id
        )
    ]


@router.post(
    "/metrics", dependencies=[Depends(require_role("device", "admin", "operator"))]
)
def post_metrics(
    payload: HeartbeatPayload,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    device = DeviceService(db).heartbeat(payload.id, payload.metrics)
    if not device:
        raise HTTPException(404, "device not found")
    ensure_organization_access(user, device.organization_id)
    return {"status": "recorded"}


@router.get("/list", dependencies=[Depends(require_permission("devices:read"))])
def list_devices(
    db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)
):
    svc = DeviceService(db)
    svc.mark_presence(organization_id=user.organization_id)
    return svc.list_devices(organization_id=user.organization_id)


@router.post("/groups", dependencies=[Depends(require_permission("devices:write"))])
def create_group(
    payload: GroupPayload,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    group = DeviceService(db).create_group(payload.name, user.organization_id)
    return {"id": group.id, "name": group.name}


@router.get("/groups", dependencies=[Depends(require_permission("devices:read"))])
def list_groups(
    db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)
):
    return [
        {"id": g.id, "name": g.name}
        for g in DeviceService(db).list_groups(organization_id=user.organization_id)
    ]


@router.post(
    "/groups/{group_id}/members",
    dependencies=[Depends(require_permission("devices:write"))],
)
def add_group_member(
    group_id: int,
    payload: GroupMemberPayload,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    svc = DeviceService(db)
    group = svc.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="group not found")
    ensure_organization_access(user, group.organization_id)
    member = svc.assign_group_member(group_id, payload.device_id)
    return {"id": member.id, "group_id": member.group_id, "device_id": member.device_id}
