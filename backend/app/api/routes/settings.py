from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from backend.app.core.auth import AuthUser, get_current_user, require_role
from backend.app.db.database import get_db
from backend.app.services.settings_service import SettingsService
from backend.app.services.system_service import SystemService

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    site_name: str | None = None
    timezone: str | None = None
    language: str | None = None
    heartbeat_interval: int | None = None
    default_playlist_id: int | None = None
    display_brightness: int | None = None
    volume: int | None = None

    def as_dict(self) -> dict:
        return self.model_dump(exclude_none=True)


class RollbackPayload(BaseModel):
    key: str = Field(min_length=1, max_length=255)
    target_version: int = Field(ge=1)


@router.get("", dependencies=[Depends(require_role("admin", "operator", "viewer"))])
def get_settings(db: Session = Depends(get_db), user: AuthUser = Depends(get_current_user)):
    return SettingsService(db).get_all(organization_id=user.organization_id)


@router.post("", dependencies=[Depends(require_role("admin", "operator"))])
def set_settings(
    payload: SettingsPayload,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    try:
        return SettingsService(db).set_many(
            payload.as_dict(),
            organization_id=user.organization_id,
            changed_by=user.username,
            reason="api_update",
            actor_role=user.role,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/apply", dependencies=[Depends(require_role("admin", "operator"))])
def apply_settings(
    payload: SettingsPayload,
    confirmed: bool = False,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    try:
        data = SettingsService(db).set_many(
            payload.as_dict(),
            organization_id=user.organization_id,
            changed_by=user.username,
            reason="apply_confirmed" if confirmed else "apply_preview",
            actor_role=user.role,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    SystemService(db)._audit(
        "settings_apply", f"confirmed={confirmed},requested_by={user.username}"
    )
    return {"applied": confirmed, "settings": data}


@router.get(
    "/history/{key}", dependencies=[Depends(require_role("admin", "operator", "viewer"))]
)
def settings_history(
    key: str,
    limit: int = 20,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    return SettingsService(db).get_history(
        key, organization_id=user.organization_id, limit=limit
    )


@router.post("/rollback", dependencies=[Depends(require_role("admin"))])
def rollback_settings(
    payload: RollbackPayload,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    try:
        return SettingsService(db).rollback(
            key=payload.key,
            target_version=payload.target_version,
            organization_id=user.organization_id,
            changed_by=user.username,
            actor_role=user.role,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
