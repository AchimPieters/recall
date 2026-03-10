from celery import Task

from backend.app.core.config import get_settings
from backend.app.db.database import SessionLocal
from backend.app.services.device_service import DeviceService
from backend.app.workers.celery_app import celery_app

settings = get_settings()


class RetryableTask(Task):
    autoretry_for = (Exception,)
    retry_backoff = True
    retry_jitter = True
    retry_kwargs = {"max_retries": settings.worker_max_retries}


def refresh_device_statuses() -> int:
    db = SessionLocal()
    try:
        return DeviceService(db).mark_presence()
    finally:
        db.close()


@celery_app.task(name="recall.workers.refresh_device_statuses", base=RetryableTask)
def refresh_device_statuses_task() -> int:
    return refresh_device_statuses()
