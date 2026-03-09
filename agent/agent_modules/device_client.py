from __future__ import annotations

import requests

from . import config
from .auth import auth_headers


def fetch_device_config(session: requests.Session) -> dict:
    response = session.get(
        f"{config.SERVER}/device/config",
        params={"device_id": config.DEVICE_ID},
        headers=auth_headers(),
        timeout=(3, 5),
        verify=config.VERIFY_TLS,
    )
    response.raise_for_status()
    return response.json()
