from __future__ import annotations

import requests

from . import config
from .auth import auth_headers


def report_version(session: requests.Session) -> dict:
    response = session.post(
        f"{config.SERVER}/device/metrics",
        json={
            "id": config.DEVICE_ID,
            "metrics": {"agent_version": config.AGENT_VERSION},
        },
        headers=auth_headers(),
        timeout=(3, 5),
        verify=config.VERIFY_TLS,
    )
    response.raise_for_status()
    return response.json()
