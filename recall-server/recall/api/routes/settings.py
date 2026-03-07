from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from recall.core.auth import AuthUser, get_current_user, require_role
from recall.db.database import get_db
from recall.services.settings_service import SettingsService
from recall.services.system_service import SystemService

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


@router.get("", dependencies=[Depends(require_role("admin", "operator", "viewer"))])
def get_settings(db: Session = Depends(get_db)):
    return SettingsService(db).get_all()


@router.post("", dependencies=[Depends(require_role("admin", "operator"))])
def set_settings(payload: SettingsPayload, db: Session = Depends(get_db)):
    try:
        return SettingsService(db).set_many(payload.as_dict())
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
        data = SettingsService(db).set_many(payload.as_dict())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    SystemService(db)._audit(
        "settings_apply", f"confirmed={confirmed},requested_by={user.username}"
    )
    return {"applied": confirmed, "settings": data}
