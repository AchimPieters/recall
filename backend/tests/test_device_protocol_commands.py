from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.database import Base
from backend.app.services.device_service import DeviceService


def _db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_device_command_fetch_ack_and_playback_status() -> None:
    db = _db_session()
    svc = DeviceService(db)
    svc.register("dev-1", "Device 1", "127.0.0.1", "1.0.0", organization_id=None)

    cmd = svc.enqueue_command(
        device_id="dev-1", command_type="reboot", payload={"delay": 0}
    )
    pending = svc.fetch_commands("dev-1")
    assert len(pending) == 1
    assert pending[0]["command_id"] == cmd["command_id"]

    acked = svc.ack_command("dev-1", cmd["command_id"], "ok", "done")
    assert acked is not None
    assert acked["status"] == "ok"

    pending_after = svc.fetch_commands("dev-1")
    assert pending_after == []

    svc.record_playback_status(
        device_id="dev-1",
        state="playing",
        media_id=5,
        position_seconds=42,
        detail="normal",
    )
    logs = svc.list_logs(limit=10)
    assert any(log.action == "playback_status" for log in logs)
