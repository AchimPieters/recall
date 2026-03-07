import os
from pathlib import Path
from uuid import uuid4

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(BASE_DIR, "recall-server", "web")
MEDIA_DIR = os.path.join(BASE_DIR, "media")
MAX_UPLOAD_BYTES = int(os.getenv("RECALL_MAX_UPLOAD_BYTES", str(100 * 1024 * 1024)))

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES

devices = {"dev-device": {"status": "online"}}


@app.route("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(WEB_DIR, path)


@app.route("/devices")
def devices_api():
    return jsonify(devices)


@app.route("/monitor")
def monitor():
    return jsonify({
        "cpu_percent": 22,
        "memory_percent": 35
    })


@app.route("/device/register", methods=["POST"])
def register():
    data = request.json or {}
    if "id" not in data:
        return jsonify({"error": "id required"}), 400

    devices[data["id"]] = {
        "id": data["id"],
        "status": data.get("status", "online")
    }
    return jsonify({"status": "registered"})


@app.route("/media/upload", methods=["POST"])
def upload():
    os.makedirs(MEDIA_DIR, exist_ok=True)

    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "file required"}), 400

    cleaned = secure_filename(Path(file.filename).name)
    if not cleaned:
        return jsonify({"error": "invalid filename"}), 400

    filename = f"{uuid4().hex}_{cleaned}"
    path = os.path.join(MEDIA_DIR, filename)
    file.save(path)

    return jsonify({"uploaded": filename, "original": cleaned})


if __name__ == "__main__":
    print("")
    print("Recall UI Development Server")
    print("http://localhost:8080")
    print("")
    app.run(host="127.0.0.1", port=8080, debug=False)
