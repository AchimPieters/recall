from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from .cache import CACHE_DIR

RECOVERY_PATH = CACHE_DIR / "recovery.json"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def record_failure(window_minutes: int = 10) -> int:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    now = _utc_now()

    payload = {"failures": []}
    if RECOVERY_PATH.exists():
        try:
            payload = json.loads(RECOVERY_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {"failures": []}

    failures = [
        ts
        for ts in payload.get("failures", [])
        if now - datetime.fromisoformat(ts) <= timedelta(minutes=window_minutes)
    ]
    failures.append(now.isoformat())
    RECOVERY_PATH.write_text(json.dumps({"failures": failures}), encoding="utf-8")
    return len(failures)


def clear_failures() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    RECOVERY_PATH.write_text(json.dumps({"failures": []}), encoding="utf-8")


def should_trigger_recovery(max_failures: int = 5, window_minutes: int = 10) -> bool:
    if not RECOVERY_PATH.exists():
        return False
    now = _utc_now()
    try:
        payload = json.loads(RECOVERY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False

    failures = [
        ts
        for ts in payload.get("failures", [])
        if now - datetime.fromisoformat(ts) <= timedelta(minutes=window_minutes)
    ]
    return len(failures) >= max_failures
