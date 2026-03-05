from fastapi import FastAPI, UploadFile
from fastapi.staticfiles import StaticFiles
import os, shutil, json, psutil

app = FastAPI()

MEDIA="/opt/recall/media"
CONFIG="/opt/recall/config.json"

os.makedirs(MEDIA,exist_ok=True)

playlist={"items":[]}
devices={}

app.mount("/web", StaticFiles(directory="recall-server/web"), name="web")

@app.get("/")
def root():
    return {"status":"recall running"}

@app.get("/playlist")
def get_playlist():
    return playlist

@app.post("/playlist")
def add_item(item:dict):
    playlist["items"].append(item)
    return {"status":"added"}

@app.post("/media/upload")
async def upload(file:UploadFile):
    path=os.path.join(MEDIA,file.filename)
    with open(path,"wb") as f:
        shutil.copyfileobj(file.file,f)
    return {"uploaded":file.filename}

@app.get("/devices")
def device_list():
    return devices

@app.post("/device/register")
def register(device:dict):
    devices[device["id"]]=device
    return {"status":"registered"}

@app.get("/monitor")
def monitor():
    return {
        "cpu":psutil.cpu_percent(),
        "memory":psutil.virtual_memory().percent
    }

@app.get("/settings")
def get_settings():
    try:
        with open(CONFIG) as f:
            return json.load(f)
    except:
        return {"rotation":0}

@app.post("/settings")
def save_settings(settings:dict):
    with open(CONFIG,"w") as f:
        json.dump(settings,f)
    return {"status":"saved"}
