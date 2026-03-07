import os
from flask import Flask, send_from_directory, jsonify, request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(BASE_DIR, "recall-server", "web")
MEDIA_DIR = os.path.join(BASE_DIR, "media")

app = Flask(__name__)

devices = {"dev-device": {"status": "online"}}

# serve index
@app.route("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")

# serve ANY html/js/css file
@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(WEB_DIR, path)


# -------- MOCK API --------

@app.route("/devices")
def devices_api():
    return jsonify(devices)

@app.route("/monitor")
def monitor():
    return jsonify({
        "cpu": 22,
        "memory": 35
    })

@app.route("/device/register", methods=["POST"])
def register():
    data = request.json
    devices[data["id"]] = data
    return jsonify({"status": "registered"})

@app.route("/media/upload", methods=["POST"])
def upload():
    os.makedirs(MEDIA_DIR, exist_ok=True)

    file = request.files["file"]
    path = os.path.join(MEDIA_DIR, file.filename)
    file.save(path)

    return jsonify({"uploaded": file.filename})


if __name__ == "__main__":
    print("")
    print("Recall UI Development Server")
    print("http://localhost:5000")
    print("")
    app.run(host="0.0.0.0", port=8080, debug=True)
