from __future__ import annotations

import json
from datetime import datetime, timezone

from .cache import CACHE_DIR

HEALTH_PATH = CACHE_DIR / "health.json"


def write_health(status: str, detail: str | None = None) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": status,
        "detail": detail or "",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    HEALTH_PATH.write_text(json.dumps(payload), encoding="utf-8")
