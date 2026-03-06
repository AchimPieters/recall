
import requests,time,socket

SERVER="http://localhost:8000"
DEVICE_ID=socket.gethostname()

while True:
    try:
        requests.post(SERVER+"/device/register",json={"id":DEVICE_ID,"status":"online"})
    except:
        pass
    time.sleep(10)
