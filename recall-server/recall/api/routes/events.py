from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from recall.core.auth import AuthUser, get_current_user, require_role
from recall.db.database import get_db
from recall.services.event_service import EventService

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", dependencies=[Depends(require_role("admin", "operator"))])
def list_events(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    return EventService(db).list_recent(
        limit=limit, organization_id=user.organization_id
    )
