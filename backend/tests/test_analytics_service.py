from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backend.app.db.database import Base, SessionLocal, engine
from backend.app.models import Device, DeviceLog, Event
from backend.app.services.analytics_service import AnalyticsService


def _seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.query(DeviceLog).delete()
        db.query(Event).delete()
        db.query(Device).delete()

        db.add_all(
            [
                Device(id="svc-1", name="S1", status="online", organization_id=11),
                Device(id="svc-2", name="S2", status="offline", organization_id=11),
                Device(id="svc-3", name="S3", status="online", organization_id=12),
            ]
        )
        db.add_all(
            [
                Event(
                    category="playback",
                    action="impression",
                    actor="agent",
                    payload="{}",
                    organization_id=11,
                ),
                Event(
                    category="playback",
                    action="impression",
                    actor="agent",
                    payload="{}",
                    organization_id=12,
                ),
            ]
        )
        now = datetime.now(timezone.utc)
        db.add_all(
            [
                DeviceLog(
                    device_id="svc-1",
                    level="error",
                    action="playback",
                    message="err",
                    timestamp=now - timedelta(hours=1),
                ),
                DeviceLog(
                    device_id="svc-3",
                    level="error",
                    action="playback",
                    message="foreign",
                    timestamp=now - timedelta(hours=1),
                ),
            ]
        )
        db.commit()
    finally:
        db.close()


def test_analytics_service_summary_and_timeseries_are_tenant_scoped() -> None:
    _seed()
    db = SessionLocal()
    try:
        service = AnalyticsService(db)
        summary = service.summary(11)
        assert summary["total_devices"] == 2
        assert summary["device_uptime_percent"] == 50.0
        assert summary["content_impressions"] == 1
        assert summary["playback_errors_24h"] == 1

        series = service.timeseries(11, 2)
        assert series["window_days"] == 2
        assert len(series["points"]) == 2
        assert series["points"][-1]["content_impressions"] == 1
        assert series["points"][-1]["playback_errors"] == 1
    finally:
        db.close()
