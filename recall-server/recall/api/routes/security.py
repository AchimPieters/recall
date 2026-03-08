from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from recall.core.auth import require_role
from recall.db.database import get_db
from recall.repositories.security_repository import SecurityRepository

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
