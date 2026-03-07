import os
import secrets
import socket
import time

import requests

SERVER = "http://localhost:8000"
DEVICE_ID = socket.gethostname()
API_KEY = os.getenv("RECALL_API_KEY")

session = requests.Session()


def register_device() -> bool:
    headers = {"x-api-key": API_KEY} if API_KEY else None
    response = session.post(
        f"{SERVER}/device/register",
        json={"id": DEVICE_ID, "status": "online"},
        headers=headers,
        timeout=(3, 5),
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
