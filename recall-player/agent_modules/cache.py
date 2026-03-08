from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CACHE_DIR = Path.home() / ".recall-agent"
CONFIG_CACHE_PATH = CACHE_DIR / "device-config.json"


def _ensure_cache_dir() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def read_cached_config() -> dict[str, Any] | None:
    if not CONFIG_CACHE_PATH.exists():
        return None
    try:
        return json.loads(CONFIG_CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def write_cached_config(config: dict[str, Any]) -> None:
    _ensure_cache_dir()
    CONFIG_CACHE_PATH.write_text(json.dumps(config), encoding="utf-8")
