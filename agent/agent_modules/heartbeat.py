import requests

from . import config
from .auth import auth_headers


def register_device(session: requests.Session) -> bool:
    response = session.post(
        f"{config.SERVER}/device/register",
        json={"id": config.DEVICE_ID, "name": config.DEVICE_ID},
        headers=auth_headers(),
        timeout=(3, 5),
        verify=config.VERIFY_TLS,
    )
    response.raise_for_status()
    return True
