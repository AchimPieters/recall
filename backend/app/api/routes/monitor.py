import psutil
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.core.auth import AuthUser, get_current_user, require_role
from backend.app.db.database import get_db
from backend.app.services.device_service import DeviceService

router = APIRouter(prefix="/monitor", tags=["monitor"])


class AlertPayload(BaseModel):
    level: str = Field(default="warning", min_length=3, max_length=32)
    source: str = Field(default="system", min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=4096)


@router.get("", dependencies=[Depends(require_role("admin", "operator", "viewer"))])
def monitor():
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return {
        "cpu_usage": psutil.cpu_percent(),
        "memory_usage": vm.percent,
        "disk_usage": disk.percent,
    }


@router.post("/alerts", dependencies=[Depends(require_role("admin", "operator"))])
def create_alert(
    payload: AlertPayload,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    alert = DeviceService(db).create_alert(
        payload.level, payload.source, payload.message, user.organization_id
    )
    return {
        "id": alert.id,
        "level": alert.level,
        "source": alert.source,
        "message": alert.message,
        "status": alert.status,
        "created_at": alert.created_at,
    }


@router.get(
    "/alerts", dependencies=[Depends(require_role("admin", "operator", "viewer"))]
)
def list_alerts(
    status: str | None = None,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    return [
        {
            "id": alert.id,
            "level": alert.level,
            "source": alert.source,
            "message": alert.message,
            "status": alert.status,
            "created_at": alert.created_at,
        }
        for alert in DeviceService(db).list_alerts(
            status=status, organization_id=user.organization_id
        )
    ]


@router.post(
    "/alerts/{alert_id}/resolve",
    dependencies=[Depends(require_role("admin", "operator"))],
)
def resolve_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    alert_obj = DeviceService(db).list_alerts(
        status=None, organization_id=user.organization_id
    )
    if user.organization_id is not None and not any(
        a.id == alert_id for a in alert_obj
    ):
        raise HTTPException(status_code=404, detail="alert not found")
    alert = DeviceService(db).resolve_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="alert not found")
    return {"id": alert.id, "status": alert.status}
