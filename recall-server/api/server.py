from fastapi import FastAPI, UploadFile
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import shutil
import psutil
import platform
import random
import json

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
MEDIA_DIR = BASE_DIR.parent / "media"

MEDIA_DIR.mkdir(exist_ok=True)

app = FastAPI()
devices = {}

app.mount("/web", StaticFiles(directory=str(WEB_DIR), html=True), name="web")


@app.get("/")
def root():
    return {"status": "recall running"}


@app.post("/device/register")
def register(device: dict):
    devices[device["id"]] = device
    return {"status": "registered"}


@app.get("/devices")
def list_devices():
    return devices


def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return round(int(f.read()) / 1000, 1)
    except:
        return round(random.uniform(40, 60), 1)   # mock temperature


@app.get("/monitor")
def monitor():

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

    except:
        # volledige mock data fallback
        return {
            "cpu_percent": random.randint(10,60),
            "memory_percent": random.randint(20,70),

            "cpu_cores": 4,
            "cpu_freq_mhz": 1500,

            "memory_total_mb": 2048,
            "memory_used_mb": random.randint(400,1200),

            "disk_percent": random.randint(30,80),
            "disk_total_gb": 32,
            "disk_used_gb": random.randint(10,20),

            "cpu_temp": random.randint(40,65),

            "system": "Linux",
            "machine": "armv7l",
            "platform": "Raspberry Pi Mock",

            "mock": True
        }


@app.post("/media/upload")
async def upload(file: UploadFile):

    path = MEDIA_DIR / file.filename

    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return {"uploaded": file.filename}
