from __future__ import annotations

from pathlib import Path

import requests

from . import config
from .auth import auth_headers


def push_playback_status(
    session: requests.Session,
    *,
    state: str,
    media_path: Path | None = None,
    detail: str | None = None,
) -> None:
    session.post(
        f"{config.SERVER}/device/playback-status",
        json={
            "id": config.DEVICE_ID,
            "state": state,
            "detail": detail,
            "position_seconds": 0,
            "media_id": None,
        },
        headers=auth_headers(),
        timeout=(3, 5),
        verify=config.VERIFY_TLS,
    ).raise_for_status()
