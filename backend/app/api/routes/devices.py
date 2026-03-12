import csv
from io import StringIO
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.core.auth import (
    AuthUser,
    ensure_organization_access,
    get_current_user,
    require_permission,
    require_role,
)
from backend.app.core.config import get_settings
from backend.app.db.database import get_db
from backend.app.models import DeviceCertificate
from backend.app.services.device_service import DeviceService

router = APIRouter(prefix="/device", tags=["devices"])

ALLOWED_DEVICE_STATUSES = {"online", "stale", "offline", "error"}


SUPPORTED_DEVICE_PROTOCOL_MAJOR = "1"
settings_conf = get_settings()




def _validate_device_certificate(*, db: Session, device_id: str, certificate_fingerprint: str | None) -> None:
    if not settings_conf.device_api_require_certificate:
        return

    fingerprint = (certificate_fingerprint or "").strip()
    if not fingerprint:
        raise HTTPException(status_code=401, detail="Device certificate fingerprint required")

    cert = db.scalar(
        select(DeviceCertificate).where(
            DeviceCertificate.device_id == device_id,
            DeviceCertificate.fingerprint == fingerprint,
        )
    )
    if cert is None:
        raise HTTPException(status_code=401, detail="Invalid device certificate fingerprint")


def _validate_device_protocol_version(
    x_device_protocol_version: str | None = Header(default="1"),
) -> str:
    version = (x_device_protocol_version or "1").strip()
    if not version:
        version = "1"

    major = version.split(".", 1)[0]
    if major != SUPPORTED_DEVICE_PROTOCOL_MAJOR:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported device protocol version '{version}'. "
                "Supported major version: 1.x"
            ),
        )
    return version



class DeviceCapabilitiesPayload(BaseModel):
    os: str | None = None
    hardware_type: str | None = None
    display_outputs: int | None = Field(default=None, ge=0)
    cpu: str | None = None
    memory_mb: int | None = Field(default=None, ge=0)
    resolution: str | None = None
    agent_version: str | None = None
    connectivity: str | None = None

    def as_dict(self) -> dict:
        return self.model_dump(exclude_none=True)




class ProvisioningTokenCreatePayload(BaseModel):
    expires_in_minutes: int = Field(default=30, ge=1, le=1440)


class DeviceEnrollPayload(BaseModel):
    provisioning_token: str = Field(min_length=16, max_length=512)
    id: str = Field(min_length=1, max_length=64)
    name: str = Field(default="Unnamed", min_length=1, max_length=255)
    version: str | None = Field(default=None, max_length=64)
    capabilities: DeviceCapabilitiesPayload | None = None

class RegisterPayload(BaseModel):
    id: str
    name: str = "Unnamed"
    version: str | None = None
    capabilities: DeviceCapabilitiesPayload | None = None


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




class CommandEnqueuePayload(BaseModel):
    device_id: str = Field(min_length=1, max_length=64)
    command_type: str = Field(min_length=1, max_length=128)
    payload: dict | None = None


class CommandAckPayload(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    command_id: str = Field(min_length=1, max_length=128)
    status: str = Field(pattern="^(ok|failed|ignored)$")
    detail: str | None = Field(default=None, max_length=1024)


class PlaybackStatusPayload(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    state: str = Field(pattern="^(idle|playing|paused|error)$")
    media_id: int | None = Field(default=None, ge=1)
    position_seconds: int | None = Field(default=None, ge=0)
    detail: str | None = Field(default=None, max_length=1024)




class TagPayload(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class DeviceTagAssignPayload(BaseModel):
    device_id: str = Field(min_length=1, max_length=64)
    tag: str = Field(min_length=1, max_length=128)


class BulkGroupActionPayload(BaseModel):
    action: str = Field(pattern="^(reboot|update|playlist_assign|rollback)$")
    target_version: str | None = Field(default=None, max_length=64)
    playlist_id: int | None = Field(default=None, ge=1)
    rollout_percentage: int = Field(default=100, ge=1, le=100)
    dry_run: bool = False




@router.post("/provisioning/token", dependencies=[Depends(require_permission("devices:write"))])
def create_provisioning_token(
    payload: ProvisioningTokenCreatePayload,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    token = DeviceService(db).create_provisioning_token(
        actor=user.username,
        organization_id=user.organization_id,
        expires_in_minutes=payload.expires_in_minutes,
    )
    return token


@router.post("/provision/enroll")
def provision_enroll(
    payload: DeviceEnrollPayload,
    request: Request,
    db: Session = Depends(get_db),
    protocol_version: str = Depends(_validate_device_protocol_version),
):
    _ = protocol_version
    svc = DeviceService(db)
    try:
        return svc.enroll_device_with_token(
            provisioning_token=payload.provisioning_token,
            device_id=payload.id,
            name=payload.name,
            ip=request.client.host if request.client else None,
            version=payload.version,
            capabilities=payload.capabilities.as_dict() if payload.capabilities else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.post(
    "/register", dependencies=[Depends(require_role("device", "admin", "operator"))]
)
def register(
    payload: RegisterPayload,
    request: Request,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
    protocol_version: str = Depends(_validate_device_protocol_version),
):
    _ = protocol_version
    svc = DeviceService(db)
    device = svc.register(
        payload.id,
        payload.name,
        request.client.host if request.client else None,
        payload.version,
        user.organization_id,
        payload.capabilities.as_dict() if payload.capabilities else None,
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
    protocol_version: str = Depends(_validate_device_protocol_version),
    certificate_fingerprint: str | None = Header(default=None, alias="X-Device-Certificate-Fingerprint"),
):
    _ = protocol_version
    _validate_device_certificate(db=db, device_id=payload.id, certificate_fingerprint=certificate_fingerprint)
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
    certificate_fingerprint: str | None = Header(default=None, alias="X-Device-Certificate-Fingerprint"),
):
    _validate_device_certificate(db=db, device_id=device_id, certificate_fingerprint=certificate_fingerprint)
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
    certificate_fingerprint: str | None = Header(default=None, alias="X-Device-Certificate-Fingerprint"),
):
    _validate_device_certificate(db=db, device_id=payload.id, certificate_fingerprint=certificate_fingerprint)
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
    certificate_fingerprint: str | None = Header(default=None, alias="X-Device-Certificate-Fingerprint"),
):
    _validate_device_certificate(db=db, device_id=payload.id, certificate_fingerprint=certificate_fingerprint)
    device = DeviceService(db).heartbeat(payload.id, payload.metrics)
    if not device:
        raise HTTPException(404, "device not found")
    ensure_organization_access(user, device.organization_id)
    return {"status": "recorded"}






@router.post(
    "/commands/enqueue", dependencies=[Depends(require_permission("devices:write"))]
)
def enqueue_command(
    payload: CommandEnqueuePayload,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    svc = DeviceService(db)
    device = svc.get_device(payload.device_id)
    if not device:
        raise HTTPException(404, "device not found")
    ensure_organization_access(user, device.organization_id)
    return svc.enqueue_command(
        device_id=payload.device_id,
        command_type=payload.command_type,
        payload=payload.payload,
        organization_id=user.organization_id,
    )


@router.get(
    "/commands", dependencies=[Depends(require_role("device", "admin", "operator"))]
)
def fetch_commands(
    device_id: str,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
    protocol_version: str = Depends(_validate_device_protocol_version),
    certificate_fingerprint: str | None = Header(default=None, alias="X-Device-Certificate-Fingerprint"),
):
    _ = protocol_version
    _validate_device_certificate(db=db, device_id=device_id, certificate_fingerprint=certificate_fingerprint)
    svc = DeviceService(db)
    device = svc.get_device(device_id)
    if not device:
        raise HTTPException(404, "device not found")
    ensure_organization_access(user, device.organization_id)
    return {"device_id": device_id, "commands": svc.fetch_commands(device_id)}


@router.post(
    "/command-ack", dependencies=[Depends(require_role("device", "admin", "operator"))]
)
def command_ack(
    payload: CommandAckPayload,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
    protocol_version: str = Depends(_validate_device_protocol_version),
    certificate_fingerprint: str | None = Header(default=None, alias="X-Device-Certificate-Fingerprint"),
):
    _ = protocol_version
    _validate_device_certificate(db=db, device_id=payload.id, certificate_fingerprint=certificate_fingerprint)
    svc = DeviceService(db)
    device = svc.get_device(payload.id)
    if not device:
        raise HTTPException(404, "device not found")
    ensure_organization_access(user, device.organization_id)
    updated = svc.ack_command(payload.id, payload.command_id, payload.status, payload.detail)
    if not updated:
        raise HTTPException(404, "command not found")
    return updated


@router.post(
    "/playback-status", dependencies=[Depends(require_role("device", "admin", "operator"))]
)
def playback_status(
    payload: PlaybackStatusPayload,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
    protocol_version: str = Depends(_validate_device_protocol_version),
    certificate_fingerprint: str | None = Header(default=None, alias="X-Device-Certificate-Fingerprint"),
):
    _ = protocol_version
    _validate_device_certificate(db=db, device_id=payload.id, certificate_fingerprint=certificate_fingerprint)
    svc = DeviceService(db)
    device = svc.get_device(payload.id)
    if not device:
        raise HTTPException(404, "device not found")
    ensure_organization_access(user, device.organization_id)
    svc.record_playback_status(
        device_id=payload.id,
        state=payload.state,
        media_id=payload.media_id,
        position_seconds=payload.position_seconds,
        detail=payload.detail,
    )
    return {"status": "recorded"}


@router.get("/list", dependencies=[Depends(require_permission("devices:read"))])
def list_devices(
    status: str | None = None,
    group_id: int | None = None,
    tag: str | None = None,
    version: str | None = None,
    last_seen_before: str | None = None,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    svc = DeviceService(db)
    svc.mark_presence(organization_id=user.organization_id)

    if status and status not in ALLOWED_DEVICE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"invalid status '{status}', expected one of: {', '.join(sorted(ALLOWED_DEVICE_STATUSES))}",
        )

    parsed_last_seen = None
    if last_seen_before:
        from datetime import datetime

        raw = last_seen_before.strip()
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        try:
            parsed_last_seen = datetime.fromisoformat(raw)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="invalid last_seen_before timestamp") from exc

    return svc.list_devices(
        organization_id=user.organization_id,
        status=status,
        group_id=group_id,
        tag=tag,
        version=version,
        last_seen_before=parsed_last_seen,
    )




@router.get("/export.csv", dependencies=[Depends(require_permission("devices:read"))])
def export_devices_csv(
    status: str | None = None,
    group_id: int | None = None,
    tag: str | None = None,
    version: str | None = None,
    last_seen_before: str | None = None,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    svc = DeviceService(db)
    svc.mark_presence(organization_id=user.organization_id)

    if status and status not in ALLOWED_DEVICE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"invalid status '{status}', expected one of: {', '.join(sorted(ALLOWED_DEVICE_STATUSES))}",
        )

    parsed_last_seen = None
    if last_seen_before:
        from datetime import datetime

        raw = last_seen_before.strip()
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        try:
            parsed_last_seen = datetime.fromisoformat(raw)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="invalid last_seen_before timestamp") from exc

    devices = svc.list_devices(
        organization_id=user.organization_id,
        status=status,
        group_id=group_id,
        tag=tag,
        version=version,
        last_seen_before=parsed_last_seen,
    )

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "name", "status", "version", "last_seen", "organization_id"])
    for device in devices:
        writer.writerow(
            [
                device.id,
                device.name,
                device.status,
                device.version or "",
                device.last_seen.isoformat() if device.last_seen else "",
                "" if device.organization_id is None else str(device.organization_id),
            ]
        )

    return PlainTextResponse(
        output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="devices.csv"'},
    )

@router.post("/groups", dependencies=[Depends(require_permission("devices:write"))])
def create_group(
    payload: GroupPayload,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    group = DeviceService(db).create_group(payload.name, user.organization_id, actor_role=user.role)
    return {"id": group.id, "name": group.name}


@router.get("/groups", dependencies=[Depends(require_permission("devices:read"))])
def list_groups(
    db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)
):
    return [
        {"id": g.id, "name": g.name}
        for g in DeviceService(db).list_groups(organization_id=user.organization_id)
    ]




@router.post("/tags", dependencies=[Depends(require_permission("devices:write"))])
def create_tag(
    payload: TagPayload,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    tag = DeviceService(db).create_tag(payload.name, user.organization_id)
    return {"id": tag.id, "name": tag.name}


@router.get("/tags", dependencies=[Depends(require_permission("devices:read"))])
def list_tags(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    return [
        {"id": t.id, "name": t.name}
        for t in DeviceService(db).list_tags(organization_id=user.organization_id)
    ]


@router.post("/tags/assign", dependencies=[Depends(require_permission("devices:write"))])
def assign_tag(
    payload: DeviceTagAssignPayload,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    svc = DeviceService(db)
    device = svc.get_device(payload.device_id)
    if not device:
        raise HTTPException(status_code=404, detail="device not found")
    ensure_organization_access(user, device.organization_id)
    return svc.assign_tag(payload.device_id, payload.tag, user.organization_id)


@router.post(
    "/groups/{group_id}/bulk",
    dependencies=[Depends(require_permission("devices:write"))],
)
def group_bulk_action(
    group_id: int,
    payload: BulkGroupActionPayload,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    svc = DeviceService(db)
    group = svc.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="group not found")
    ensure_organization_access(user, group.organization_id)

    try:
        result = svc.execute_group_action(
            group_id=group_id,
            action=payload.action,
            actor=user.username,
            organization_id=user.organization_id,
            target_version=payload.target_version,
            playlist_id=payload.playlist_id,
            rollout_percentage=payload.rollout_percentage,
            dry_run=payload.dry_run,
            actor_role=user.role,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


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
    member = svc.assign_group_member(group_id, payload.device_id, actor_role=user.role)
    return {"id": member.id, "group_id": member.group_id, "device_id": member.device_id}
