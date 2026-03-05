from fastapi import FastAPI, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.websockets import WebSocket
import os, shutil, json, psutil

app = FastAPI()

MEDIA="/opt/recall/media"
CONFIG="/opt/recall/config.json"

devices={}
playlist={"items":[]}

os.makedirs(MEDIA,exist_ok=True)

app.mount("/web", StaticFiles(directory="recall-server/web"), name="web")

@app.get("/playlist")
def get_playlist():
    return playlist

@app.post("/playlist")
def add(item:dict):
    playlist["items"].append(item)
    return {"status":"ok"}

@app.post("/media/upload")
async def upload(file:UploadFile):
    path=os.path.join(MEDIA,file.filename)
    with open(path,"wb") as f:
        shutil.copyfileobj(file.file,f)
    return {"uploaded":file.filename}

@app.get("/devices")
def fleet():
    return devices

@app.post("/device/register")
def register(device:dict):
    devices[device["id"]]=device
    return {"status":"registered"}

@app.post("/device/update")
def remote_update():
    return {"update":"triggered"}

@app.get("/monitor")
def monitor():
    return {
        "cpu":psutil.cpu_percent(),
        "mem":psutil.virtual_memory().percent
    }

@app.websocket("/preview")
async def preview(ws:WebSocket):
    await ws.accept()
    while True:
        await ws.send_text("preview-stream")
