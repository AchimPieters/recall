import os
import secrets
import socket
import time

import requests

SERVER = os.getenv("RECALL_SERVER_URL", "https://localhost:8000")
DEVICE_ID = socket.gethostname()
API_KEY = os.getenv("RECALL_API_KEY")
ACCESS_TOKEN = os.getenv("RECALL_ACCESS_TOKEN")
VERIFY_TLS = os.getenv("RECALL_VERIFY_TLS", "true").lower() == "true"

session = requests.Session()


def _auth_headers() -> dict[str, str] | None:
    if ACCESS_TOKEN:
        return {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    if API_KEY:
        return {"x-api-key": API_KEY}
    return None


def register_device() -> bool:
    response = session.post(
        f"{SERVER}/device/register",
        json={"id": DEVICE_ID, "name": DEVICE_ID},
        headers=_auth_headers(),
        timeout=(3, 5),
        verify=VERIFY_TLS,
    )
    response.raise_for_status()
    return True


backoff = 5
while True:
    try:
        register_device()
        backoff = 10
    except requests.RequestException:
        backoff = min(backoff * 2, 120)

    sleep_for = backoff + (secrets.randbelow(1000) / 1000)
    time.sleep(sleep_for)
