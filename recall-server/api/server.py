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
import json
import re
import subprocess
from uuid import uuid4

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
MEDIA_DIR = BASE_DIR.parent / "media"
SETTINGS_FILE = BASE_DIR / "settings.json"
BOOT_CONFIG_FILE = Path("/boot/config.txt")

MEDIA_DIR.mkdir(exist_ok=True)

app = FastAPI()
devices = {}
API_KEY = os.getenv("RECALL_API_KEY")
MAX_UPLOAD_BYTES = int(os.getenv("RECALL_MAX_UPLOAD_BYTES", str(100 * 1024 * 1024)))

logger = logging.getLogger("recall.api")


class DeviceRegistration(BaseModel):
    id: str
    status: str = "online"


class SettingsPayload(BaseModel):
    device_name: str = "Recall"
    kiosk_mode: bool = False
    resolution: str = ""
    display_rotate: int = 0
    hdmi_group: int = 1
    hdmi_mode: int = 16
    brightness: float = 1.0


def require_api_key(request: Request):
    if not API_KEY:
        return

    provided = request.headers.get("x-api-key")
    if provided != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


def default_settings() -> dict:
    return SettingsPayload().model_dump()


def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            data = json.loads(SETTINGS_FILE.read_text())
            return {**default_settings(), **data}
        except (json.JSONDecodeError, OSError):
            pass
    return default_settings()


def save_settings(data: dict) -> None:
    SETTINGS_FILE.write_text(json.dumps(data, indent=2))


def update_boot_config(display_rotate: int, hdmi_group: int, hdmi_mode: int) -> dict:
    if not BOOT_CONFIG_FILE.exists():
        return {"updated": False, "reason": "/boot/config.txt not found"}

    text = BOOT_CONFIG_FILE.read_text()
    lines = text.splitlines()

    wanted = {
        "display_rotate": str(display_rotate),
        "hdmi_group": str(hdmi_group),
        "hdmi_mode": str(hdmi_mode),
    }

    found = {k: False for k in wanted}
    updated_lines = []
    for line in lines:
        stripped = line.strip()
        replaced = False
        for key, value in wanted.items():
            if re.match(rf"^#?\s*{key}=", stripped):
                updated_lines.append(f"{key}={value}")
                found[key] = True
                replaced = True
                break
        if not replaced:
            updated_lines.append(line)

    for key, value in wanted.items():
        if not found[key]:
            updated_lines.append(f"{key}={value}")

    BOOT_CONFIG_FILE.write_text("\n".join(updated_lines) + "\n")
    return {"updated": True, "file": str(BOOT_CONFIG_FILE)}


def run_cmd(cmd: list[str]) -> dict:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        return {
            "ok": proc.returncode == 0,
            "code": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "cmd": " ".join(cmd),
        }
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "error": str(exc), "cmd": " ".join(cmd)}


def detect_display() -> dict:
    result = run_cmd(["xrandr", "--query"])
    if not result.get("ok"):
        return result

    outputs = []
    for line in result.get("stdout", "").splitlines():
        if " connected" in line:
            outputs.append(line)

    return {"ok": True, "outputs": outputs, "raw": result.get("stdout", "")}


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
        return round(40 + (secrets.randbelow(200) / 10), 1)


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


@app.get("/settings")
def get_settings():
    return load_settings()


@app.post("/settings")
def set_settings(payload: SettingsPayload):
    data = payload.model_dump()
    save_settings(data)
    return {"saved": True, "settings": data}


@app.post("/settings/apply")
def apply_settings(payload: SettingsPayload):
    data = payload.model_dump()
    save_settings(data)

    boot = update_boot_config(data["display_rotate"], data["hdmi_group"], data["hdmi_mode"])
    brightness = run_cmd(["xrandr", "--output", "HDMI-1", "--brightness", str(data["brightness"])])

    kiosk_cmd = ["pkill", "-f", "chromium --kiosk"]
    if data["kiosk_mode"]:
        kiosk_cmd = ["bash", "-lc", "nohup chromium --kiosk >/tmp/recall-kiosk.log 2>&1 &"]
    kiosk = run_cmd(kiosk_cmd)

    return {
        "applied": True,
        "boot_config": boot,
        "brightness": brightness,
        "kiosk": kiosk,
        "settings": data,
    }


@app.get("/display/detect")
def display_detect():
    return detect_display()


@app.get("/display/hdmi/auto")
def display_hdmi_auto():
    detected = detect_display()
    if not detected.get("ok"):
        return {"ok": False, "detected": detected, "hdmi_group": 1, "hdmi_mode": 16}

    text = "\n".join(detected.get("outputs", []))
    mode = 16
    if "3840x2160" in detected.get("raw", ""):
        mode = 95
    elif "1280x720" in detected.get("raw", ""):
        mode = 4

    return {"ok": True, "detected": text, "hdmi_group": 1, "hdmi_mode": mode}


@app.post("/system/reboot")
def system_reboot():
    result = run_cmd(["systemctl", "reboot"])
    return {"requested": True, "result": result}


@app.post("/system/update")
def system_update():
    script = BASE_DIR.parent / "update.sh"
    if script.exists():
        result = run_cmd(["bash", str(script)])
    else:
        result = {"ok": False, "error": f"Script not found: {script}"}
    return {"requested": True, "result": result}
