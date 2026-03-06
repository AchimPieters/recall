
from fastapi import FastAPI, UploadFile
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import shutil, psutil

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
MEDIA_DIR = BASE_DIR.parent / "media"

MEDIA_DIR.mkdir(exist_ok=True)

app = FastAPI()
devices = {}

app.mount("/web", StaticFiles(directory=str(WEB_DIR), html=True), name="web")

@app.get("/")
def root():
    return {"status":"recall running"}

@app.post("/device/register")
def register(device:dict):
    devices[device["id"]] = device
    return {"status":"registered"}

@app.get("/devices")
def list_devices():
    return devices

@app.get("/monitor")
def monitor():
    return {
        "cpu": psutil.cpu_percent(),
        "memory": psutil.virtual_memory().percent
    }

@app.post("/media/upload")
async def upload(file: UploadFile):
    path = MEDIA_DIR / file.filename
    with open(path,"wb") as f:
        shutil.copyfileobj(file.file,f)
    return {"uploaded": file.filename}
