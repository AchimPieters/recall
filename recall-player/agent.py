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
ALLOW_API_KEY_FALLBACK = (
    os.getenv("RECALL_AGENT_ALLOW_API_KEY", "false").lower() == "true"
)

session = requests.Session()


def _auth_headers() -> dict[str, str] | None:
    if ACCESS_TOKEN:
        return {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    if API_KEY and ALLOW_API_KEY_FALLBACK:
        return {"x-api-key": API_KEY}
    return None


def _validate_runtime_config() -> None:
    if not SERVER.startswith("https://") and VERIFY_TLS:
        raise RuntimeError(
            "Refusing insecure RECALL_SERVER_URL while TLS verification is enabled"
        )
    if API_KEY and not ACCESS_TOKEN and not ALLOW_API_KEY_FALLBACK:
        raise RuntimeError(
            "RECALL_API_KEY without RECALL_ACCESS_TOKEN is blocked by default; "
            "set RECALL_AGENT_ALLOW_API_KEY=true to explicitly allow legacy mode"
        )


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
_validate_runtime_config()
while True:
    try:
        register_device()
        backoff = 10
    except requests.RequestException:
        backoff = min(backoff * 2, 120)

    sleep_for = backoff + (secrets.randbelow(1000) / 1000)
    time.sleep(sleep_for)
