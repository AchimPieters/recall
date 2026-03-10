from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from backend.app.core.auth import AuthUser, get_current_user, require_role
from backend.app.db.database import get_db
from backend.app.services.settings_service import (
    ALLOWED_SCOPES,
    SCOPE_DEVICE,
    SCOPE_ORGANIZATION,
    SettingsService,
)
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
    scope: str = Field(default=SCOPE_ORGANIZATION)
    device_id: str | None = Field(default=None, max_length=64)


def _resolve_scope(
    *,
    scope: str,
    user: AuthUser,
    device_id: str | None,
) -> tuple[str, int | None, str | None]:
    if scope not in ALLOWED_SCOPES:
        raise HTTPException(status_code=400, detail=f"Invalid scope. Allowed: {sorted(ALLOWED_SCOPES)}")
    if scope == SCOPE_ORGANIZATION:
        return scope, user.organization_id, None
    if scope == SCOPE_DEVICE:
        return scope, user.organization_id, device_id
    return scope, None, None


@router.get("", dependencies=[Depends(require_role("admin", "operator", "viewer"))])
def get_settings(
    scope: str = Query(default=SCOPE_ORGANIZATION),
    device_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    resolved_scope, org_id, resolved_device_id = _resolve_scope(
        scope=scope,
        user=user,
        device_id=device_id,
    )
    try:
        return SettingsService(db).get_all(
            scope=resolved_scope,
            organization_id=org_id,
            device_id=resolved_device_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("", dependencies=[Depends(require_role("admin", "operator"))])
def set_settings(
    payload: SettingsPayload,
    scope: str = Query(default=SCOPE_ORGANIZATION),
    device_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    resolved_scope, org_id, resolved_device_id = _resolve_scope(
        scope=scope,
        user=user,
        device_id=device_id,
    )
    try:
        return SettingsService(db).set_many(
            payload.as_dict(),
            scope=resolved_scope,
            organization_id=org_id,
            device_id=resolved_device_id,
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
    scope: str = Query(default=SCOPE_ORGANIZATION),
    device_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    resolved_scope, org_id, resolved_device_id = _resolve_scope(
        scope=scope,
        user=user,
        device_id=device_id,
    )
    try:
        data = SettingsService(db).set_many(
            payload.as_dict(),
            scope=resolved_scope,
            organization_id=org_id,
            device_id=resolved_device_id,
            changed_by=user.username,
            reason="apply_confirmed" if confirmed else "apply_preview",
            actor_role=user.role,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    SystemService(db)._audit(
        "settings_apply",
        f"confirmed={confirmed},requested_by={user.username},scope={resolved_scope},device_id={resolved_device_id}",
    )
    return {"applied": confirmed, "settings": data}


@router.get(
    "/history/{key}", dependencies=[Depends(require_role("admin", "operator", "viewer"))]
)
def settings_history(
    key: str,
    limit: int = 20,
    scope: str = Query(default=SCOPE_ORGANIZATION),
    device_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    resolved_scope, org_id, resolved_device_id = _resolve_scope(
        scope=scope,
        user=user,
        device_id=device_id,
    )
    return SettingsService(db).get_history(
        key,
        scope=resolved_scope,
        organization_id=org_id,
        device_id=resolved_device_id,
        limit=limit,
    )


@router.post("/rollback", dependencies=[Depends(require_role("admin"))])
def rollback_settings(
    payload: RollbackPayload,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    resolved_scope, org_id, resolved_device_id = _resolve_scope(
        scope=payload.scope,
        user=user,
        device_id=payload.device_id,
    )
    try:
        return SettingsService(db).rollback(
            key=payload.key,
            target_version=payload.target_version,
            scope=resolved_scope,
            organization_id=org_id,
            device_id=resolved_device_id,
            changed_by=user.username,
            actor_role=user.role,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
