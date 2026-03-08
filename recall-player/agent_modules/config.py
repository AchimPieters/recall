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
