from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.auth import AuthUser, get_current_user, require_permission
from backend.app.core.security import hash_token
from backend.app.db.database import get_db
from backend.app.models import PublicApiKey

router = APIRouter(prefix="/public-api/keys", tags=["public-api-keys"])


class PublicApiKeyCreatePayload(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    rate_limit_per_minute: int = Field(default=60, ge=1, le=5000)
    organization_id: int | None = None


class PublicApiKeyStatusPayload(BaseModel):
    is_active: bool


@router.get("", dependencies=[Depends(require_permission("settings:read"))])
def list_public_api_keys(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    stmt = select(PublicApiKey).order_by(PublicApiKey.id.desc())
    if user.organization_id is not None:
        stmt = stmt.where(PublicApiKey.organization_id == user.organization_id)
    rows = db.scalars(stmt).all()
    return [
        {
            "id": row.id,
            "name": row.name,
            "organization_id": row.organization_id,
            "rate_limit_per_minute": row.rate_limit_per_minute,
            "is_active": row.is_active,
            "created_by": row.created_by,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@router.post("", dependencies=[Depends(require_permission("settings:write"))])
def create_public_api_key(
    payload: PublicApiKeyCreatePayload,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    if (
        user.organization_id is not None
        and payload.organization_id != user.organization_id
    ):
        raise HTTPException(
            status_code=403, detail="Cross-organization key creation denied"
        )

    raw_key = secrets.token_urlsafe(24)
    row = PublicApiKey(
        name=payload.name.strip(),
        organization_id=(
            payload.organization_id
            if user.organization_id is None
            else user.organization_id
        ),
        key_hash=hash_token(raw_key),
        rate_limit_per_minute=payload.rate_limit_per_minute,
        is_active=True,
        created_by=user.username,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "api_key": raw_key,
        "name": row.name,
        "organization_id": row.organization_id,
        "rate_limit_per_minute": row.rate_limit_per_minute,
        "is_active": row.is_active,
    }


@router.patch("/{key_id}", dependencies=[Depends(require_permission("settings:write"))])
def update_public_api_key_status(
    key_id: int,
    payload: PublicApiKeyStatusPayload,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    row = db.get(PublicApiKey, key_id)
    if not row:
        raise HTTPException(status_code=404, detail="public api key not found")
    if user.organization_id is not None and row.organization_id != user.organization_id:
        raise HTTPException(
            status_code=403, detail="Cross-organization key update denied"
        )

    row.is_active = payload.is_active
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "is_active": row.is_active,
    }
