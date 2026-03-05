from fastapi import FastAPI, UploadFile
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import shutil, psutil, json

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
MEDIA_DIR = BASE_DIR.parent / "media"

MEDIA_DIR.mkdir(exist_ok=True)

app = FastAPI()

playlist = {"items": []}
devices = {}

app.mount("/web", StaticFiles(directory=str(WEB_DIR)), name="web")

@app.get("/")
def root():
    return {"status": "recall running"}

@app.get("/playlist")
def get_playlist():
    return playlist

@app.post("/playlist")
def add_item(item: dict):
    playlist["items"].append(item)
    return {"status": "added"}

@app.post("/media/upload")
async def upload(file: UploadFile):
    path = MEDIA_DIR / file.filename
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"uploaded": file.filename}

@app.post("/device/register")
def register(device: dict):
    devices[device["id"]] = device
    return {"status": "registered"}

@app.get("/devices")
def list_devices():
    return devices

@app.get("/monitor")
def monitor():
    return {
        "cpu": psutil.cpu_percent(),
        "memory": psutil.virtual_memory().percent
    }
