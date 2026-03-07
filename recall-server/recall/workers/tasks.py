from recall.db.database import SessionLocal
from recall.services.device_service import DeviceService


def refresh_device_statuses() -> int:
    db = SessionLocal()
    try:
        return DeviceService(db).mark_presence()
    finally:
        db.close()
