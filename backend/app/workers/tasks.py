from backend.app.db.database import SessionLocal
from backend.app.services.device_service import DeviceService
from backend.app.workers.celery_app import celery_app


def refresh_device_statuses() -> int:
    db = SessionLocal()
    try:
        return DeviceService(db).mark_presence()
    finally:
        db.close()


@celery_app.task(name="recall.workers.refresh_device_statuses")
def refresh_device_statuses_task() -> int:
    return refresh_device_statuses()
