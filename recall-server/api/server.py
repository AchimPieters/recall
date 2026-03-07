from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
import psutil
import platform
import secrets
import logging
import os
import time
from uuid import uuid4

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
MEDIA_DIR = BASE_DIR.parent / "media"

MEDIA_DIR.mkdir(exist_ok=True)

app = FastAPI()
devices = {}
API_KEY = os.getenv("RECALL_API_KEY")
MAX_UPLOAD_BYTES = int(os.getenv("RECALL_MAX_UPLOAD_BYTES", str(100 * 1024 * 1024)))

logger = logging.getLogger("recall.api")


class DeviceRegistration(BaseModel):
    id: str
    status: str = "online"


def require_api_key(request: Request):
    if not API_KEY:
        return

    provided = request.headers.get("x-api-key")
    if provided != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

app.mount("/web", StaticFiles(directory=str(WEB_DIR), html=True), name="web")


@app.get("/")
def root():
    return {"status": "recall running"}


@app.post("/device/register")
def register(device: DeviceRegistration, request: Request):
    require_api_key(request)
    devices[device.id] = {
        "id": device.id,
        "status": device.status,
        "last_seen": int(time.time())
    }
    return {"status": "registered"}


@app.get("/devices")
def list_devices(request: Request):
    require_api_key(request)
    return devices


def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return round(int(f.read()) / 1000, 1)
    except (FileNotFoundError, PermissionError, ValueError):
        return round(40 + (secrets.randbelow(200) / 10), 1)   # mock temperature


@app.get("/monitor")
def monitor(request: Request):
    require_api_key(request)

    try:
        cpu = psutil.cpu_percent()
        vm = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        cpu_freq = psutil.cpu_freq()

        return {
            "cpu_percent": cpu,
            "memory_percent": vm.percent,

            "cpu_cores": psutil.cpu_count(),
            "cpu_freq_mhz": cpu_freq.current if cpu_freq else 1500,

            "memory_total_mb": round(vm.total / 1024 / 1024),
            "memory_used_mb": round(vm.used / 1024 / 1024),

            "disk_percent": disk.percent,
            "disk_total_gb": round(disk.total / 1024 / 1024 / 1024, 1),
            "disk_used_gb": round(disk.used / 1024 / 1024 / 1024, 1),

            "cpu_temp": get_cpu_temp(),

            "system": platform.system(),
            "machine": platform.machine(),
            "platform": platform.platform(),

            "mock": False
        }

    except (OSError, ValueError) as exc:
        logger.warning("Returning mock monitor data due to read error: %s", exc)
        # volledige mock data fallback
        return {
            "cpu_percent": 10 + secrets.randbelow(51),
            "memory_percent": 20 + secrets.randbelow(51),

            "cpu_cores": 4,
            "cpu_freq_mhz": 1500,

            "memory_total_mb": 2048,
            "memory_used_mb": 400 + secrets.randbelow(801),

            "disk_percent": 30 + secrets.randbelow(51),
            "disk_total_gb": 32,
            "disk_used_gb": 10 + secrets.randbelow(11),

            "cpu_temp": 40 + secrets.randbelow(26),

            "system": "Linux",
            "machine": "armv7l",
            "platform": "Raspberry Pi Mock",

            "mock": True
        }


@app.post("/media/upload")
async def upload(file: UploadFile, request: Request):
    require_api_key(request)

    filename = Path(file.filename or "upload.bin").name
    if not filename or filename in {".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid filename")

    target_name = f"{uuid4().hex}_{filename}"
    path = MEDIA_DIR / target_name

    total = 0
    with open(path, "wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break

            total += len(chunk)
            if total > MAX_UPLOAD_BYTES:
                path.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="Upload too large")
            f.write(chunk)

    await file.close()

    return {"uploaded": target_name, "original": filename, "size": total}
