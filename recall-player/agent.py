import requests, time

SERVER="http://localhost:8000"

while True:
    try:
        requests.post(SERVER + "/device/register", json={
            "id": "display-1",
            "status": "online"
        })
    except:
        pass

    time.sleep(10)
