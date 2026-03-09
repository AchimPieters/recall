from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .cache import CACHE_DIR

LOG_PATH = CACHE_DIR / "agent.log"


def append_log(level: str, message: str) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    LOG_PATH.write_text(
        (LOG_PATH.read_text(encoding="utf-8") if LOG_PATH.exists() else "")
        + f"{timestamp} [{level.upper()}] {message}\n",
        encoding="utf-8",
    )
