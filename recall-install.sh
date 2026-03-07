#!/bin/bash

set -e

INSTALL_DIR="/opt/recall"

echo "Installing Recall..."

sudo apt update

sudo apt install -y python3 python3-pip git mpv gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-libav

pip3 install fastapi uvicorn websockets psutil python-multipart requests

sudo mkdir -p "$INSTALL_DIR"

sudo cp -r recall-server "$INSTALL_DIR/"
sudo cp -r recall-player "$INSTALL_DIR/"
sudo cp -r layouts "$INSTALL_DIR/"
sudo mkdir -p "$INSTALL_DIR/media"

echo "Installation finished"

echo "Start server with:"
echo "cd /opt/recall/recall-server/api"
echo "uvicorn server:app --host 0.0.0.0 --port 8000"
