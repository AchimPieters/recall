from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.core.auth import AuthUser, get_current_user, require_permission
from backend.app.db.database import get_db
from backend.app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", dependencies=[Depends(require_permission("monitor.read"))])
def analytics_summary(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    service = AnalyticsService(db)
    return service.summary(user.organization_id)


@router.get("/timeseries", dependencies=[Depends(require_permission("monitor.read"))])
def analytics_timeseries(
    days: int = Query(default=7, ge=1, le=30),
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    service = AnalyticsService(db)
    return service.timeseries(user.organization_id, days)
