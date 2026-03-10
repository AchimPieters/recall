from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.auth import AuthUser, get_current_user, require_role
from backend.app.db.database import get_db
from backend.app.repositories.security_repository import SecurityRepository

router = APIRouter(prefix="/security", tags=["security"])


@router.get(
    "/audit",
    dependencies=[Depends(require_role("admin"))],
)
def list_security_audit_events(
    limit: int = 100,
    actor: str | None = None,
    event_type: str | None = None,
    db: Session = Depends(get_db),
):
    rows = SecurityRepository(db).list_security_events(
        limit=max(1, min(limit, 500)), actor=actor, event_type=event_type
    )
    return [
        {
            "id": row.id,
            "actor": row.actor,
            "event_type": row.event_type,
            "detail": row.detail,
            "ip_address": row.ip_address,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@router.get(
    "/audit/logs",
    dependencies=[Depends(require_role("admin", "operator"))],
)
def list_audit_logs(
    limit: int = 100,
    actor_type: str | None = None,
    actor_id: str | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    ip_address: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    rows = SecurityRepository(db).list_audit_logs(
        limit=max(1, min(limit, 500)),
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        created_from=created_from,
        created_to=created_to,
        organization_id=user.organization_id,
    )
    return [
        {
            "id": row.id,
            "actor_type": row.actor_type,
            "actor_id": row.actor_id,
            "organization_id": row.organization_id,
            "action": row.action,
            "resource_type": row.resource_type,
            "resource_id": row.resource_id,
            "before_state": row.before_state,
            "after_state": row.after_state,
            "ip_address": row.ip_address,
            "user_agent": row.user_agent,
            "created_at": row.created_at,
        }
        for row in rows
    ]
