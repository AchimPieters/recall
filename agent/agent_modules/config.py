from pathlib import Path
import os
import socket

SERVER = os.getenv("RECALL_SERVER_URL", "https://localhost:8000")
DEVICE_ID = socket.gethostname()
API_KEY = os.getenv("RECALL_API_KEY")
ACCESS_TOKEN = os.getenv("RECALL_ACCESS_TOKEN")
VERIFY_TLS = os.getenv("RECALL_VERIFY_TLS", "true").lower() == "true"
ALLOW_API_KEY_FALLBACK = (
    os.getenv("RECALL_AGENT_ALLOW_API_KEY", "false").lower() == "true"
)

AGENT_VERSION = os.getenv("RECALL_AGENT_VERSION", "2.0.0")
MEDIA_CACHE_DIR = Path(
    os.getenv("RECALL_MEDIA_CACHE_DIR", str(Path.home() / ".recall-cache"))
)

RECOVERY_WINDOW_MINUTES = int(os.getenv("RECALL_RECOVERY_WINDOW_MINUTES", "10"))
RECOVERY_MAX_FAILURES = int(os.getenv("RECALL_RECOVERY_MAX_FAILURES", "5"))
