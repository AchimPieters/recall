from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest
from sqlalchemy.orm import Session

from backend.app.core.auth import AuthUser, get_current_user, require_role
from backend.app.core.config import get_settings
from backend.app.db.database import get_db
from backend.app.services.device_service import DeviceService
from backend.app.services.platform_service import PlatformService
from backend.app.workers.celery_app import get_worker_snapshot

router = APIRouter(tags=["platform"])
settings_conf = get_settings()

device_count = Gauge("device_count", "Total devices")
device_online = Gauge("device_online", "Online devices")


def _resolve_scope(user: AuthUser) -> tuple[int | None, bool]:
    if user.organization_id is not None:
        return user.organization_id, False
    if user.role in {"admin", "superadmin"}:
        return None, True
    raise HTTPException(status_code=403, detail="Organization context required")


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
    PlatformService(db).check_ready()
    return {"status": "ready"}


@router.get("/devices")
def devices_summary(
    db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)
):
    org_scope, include_all_tenants = _resolve_scope(user)
    svc = DeviceService(db)
    svc.mark_presence(organization_id=org_scope)
    devices_list = svc.list_devices(
        organization_id=None if include_all_tenants else org_scope
    )
    device_count.set(len(devices_list))
    device_online.set(len([d for d in devices_list if d.status == "online"]))
    return devices_list


@router.get("/metrics")
def metrics():
    return PlainTextResponse(
        generate_latest().decode("utf-8"), media_type=CONTENT_TYPE_LATEST
    )


@router.get(
    "/workers/status", dependencies=[Depends(require_role("admin", "operator"))]
)
def workers_status():
    return get_worker_snapshot()


@router.get(
    "/observability/summary", dependencies=[Depends(require_role("admin", "operator"))]
)
def observability_summary(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    org_scope, include_all_tenants = _resolve_scope(user)
    svc = DeviceService(db)
    devices_list = svc.list_devices(
        organization_id=None if include_all_tenants else org_scope
    )

    alert_counts = PlatformService(db).alert_counts(
        organization_id=None if include_all_tenants else org_scope
    )

    return {
        "devices": {
            "total": len(devices_list),
            "online": len([d for d in devices_list if d.status == "online"]),
        },
        "alerts": alert_counts,
        "workers": get_worker_snapshot(),
    }
