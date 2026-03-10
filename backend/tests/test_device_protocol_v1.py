from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.database import Base
from backend.app.services.device_service import DeviceService


def _db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_register_persists_device_capabilities() -> None:
    db = _db_session()
    svc = DeviceService(db)

    device = svc.register(
        "dev-cap-1",
        "Device Cap",
        "127.0.0.1",
        "1.2.3",
        organization_id=None,
        capabilities={
            "os": "linux",
            "hardware_type": "rpi",
            "display_outputs": 1,
            "cpu": "armv8",
            "memory_mb": 2048,
            "resolution": "1920x1080",
            "agent_version": "2.0.0",
            "connectivity": "ethernet",
        },
    )

    assert device.capabilities is not None
    assert device.capabilities["os"] == "linux"
    assert device.capabilities["agent_version"] == "2.0.0"


def test_status_derivation_online_stale_offline_and_error() -> None:
    db = _db_session()
    svc = DeviceService(db)

    device = svc.register("dev-state-1", "Device State", None, "1.0.0", None)

    # recent heartbeat = online
    svc.heartbeat("dev-state-1", {"cpu": 10, "state": "ok"})
    svc.mark_presence()
    assert svc.get_device("dev-state-1").status == "online"

    # old heartbeat = stale
    device.last_seen = datetime.now(timezone.utc) - timedelta(seconds=40)
    db.commit()
    svc.mark_presence()
    assert svc.get_device("dev-state-1").status in {"stale", "offline"}

    # very old heartbeat = offline
    device.last_seen = datetime.now(timezone.utc) - timedelta(days=1)
    db.commit()
    svc.mark_presence()
    assert svc.get_device("dev-state-1").status == "offline"

    # explicit error metric keeps error state
    svc.heartbeat("dev-state-1", {"state": "error", "detail": "playback failure"})
    svc.mark_presence()
    assert svc.get_device("dev-state-1").status == "error"
