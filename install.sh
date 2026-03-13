#!/usr/bin/env bash
set -e

INSTALL_DIR="/opt/recall"
REPO="https://github.com/AchimPieters/recall.git"

echo "Installing Recall..."

sudo apt update

# Detect chromium package name
if apt-cache show chromium >/dev/null 2>&1; then
    BROWSER="chromium"
else
    BROWSER="chromium-browser"
fi

sudo apt install -y git curl python3 python3-venv python3-pip mpv "$BROWSER" gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-libav

sudo rm -rf "$INSTALL_DIR"
sudo git clone "$REPO" "$INSTALL_DIR"
sudo chown -R "$USER":"$USER" "$INSTALL_DIR"

cd "$INSTALL_DIR"

python3 -m venv venv
# shellcheck disable=SC1091
source venv/bin/activate

pip install --upgrade pip
pip install fastapi uvicorn psutil requests python-multipart

mkdir -p media

sudo tee /etc/systemd/system/recall-backend.service > /dev/null <<EOF_SERVICE
[Unit]
Description=Recall Backend API
After=network.target

[Service]
User=$USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/uvicorn backend.app.api.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF_SERVICE

sudo tee /etc/systemd/system/recall-agent.service > /dev/null <<EOF_SERVICE
[Unit]
Description=Recall Agent
After=network.target

[Service]
User=$USER
WorkingDirectory=$INSTALL_DIR/agent
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/agent/agent.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF_SERVICE

sudo systemctl daemon-reload
sudo systemctl enable recall-backend
sudo systemctl enable recall-agent
sudo systemctl start recall-backend
sudo systemctl start recall-agent

IP=$(hostname -I | awk '{print $1}')

echo ""
echo "Recall installed successfully"
echo "Dashboard: http://$IP:8000/web"
