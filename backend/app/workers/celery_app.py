from celery import Celery

from backend.app.core.config import get_settings
from backend.app.core.tracing import init_tracing

settings = get_settings()
init_tracing("recall-worker")

celery_app = Celery(
    "recall",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_retry_delay=settings.worker_default_retry_delay_seconds,
)


def get_worker_snapshot() -> dict:
    inspect = celery_app.control.inspect(timeout=1.0)
    try:
        stats = inspect.stats() or {}
        active = inspect.active() or {}
        scheduled = inspect.scheduled() or {}
        reserved = inspect.reserved() or {}
    except Exception as exc:  # noqa: BLE001
        return {
            "available": False,
            "error": str(exc),
            "workers": {},
        }

    workers = sorted(
        set(stats.keys())
        | set(active.keys())
        | set(scheduled.keys())
        | set(reserved.keys())
    )
    return {
        "available": bool(workers),
        "workers": {
            worker: {
                "active": len(active.get(worker, []) or []),
                "scheduled": len(scheduled.get(worker, []) or []),
                "reserved": len(reserved.get(worker, []) or []),
            }
            for worker in workers
        },
    }
