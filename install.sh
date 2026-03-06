
#!/usr/bin/env bash
set -e

INSTALL_DIR="/opt/recall"
REPO="https://github.com/AchimPieters/recall.git"

echo "================================="
echo " Recall v1 Production Installer"
echo "================================="

sudo apt update

# Detect correct Chromium package
if apt-cache show chromium >/dev/null 2>&1; then
    BROWSER="chromium"
else
    BROWSER="chromium-browser"
fi

echo "Using browser package: $BROWSER"

sudo apt install -y git curl python3 python3-venv python3-pip mpv $BROWSER gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-libav

echo "Installing Recall to $INSTALL_DIR"

sudo rm -rf $INSTALL_DIR
sudo git clone $REPO $INSTALL_DIR
sudo chown -R $USER:$USER $INSTALL_DIR

cd $INSTALL_DIR

python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install fastapi uvicorn psutil requests python-multipart

mkdir -p media

echo "Creating systemd services..."

sudo tee /etc/systemd/system/recall-server.service > /dev/null <<EOF
[Unit]
Description=Recall Server
After=network.target

[Service]
User=$USER
WorkingDirectory=$INSTALL_DIR/recall-server/api
ExecStart=$INSTALL_DIR/venv/bin/uvicorn server:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/recall-player.service > /dev/null <<EOF
[Unit]
Description=Recall Player
After=network.target

[Service]
User=$USER
WorkingDirectory=$INSTALL_DIR/recall-player
ExecStart=$INSTALL_DIR/venv/bin/python agent.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/recall-kiosk.service > /dev/null <<EOF
[Unit]
Description=Recall Chromium Kiosk
After=graphical.target

[Service]
User=$USER
Environment=DISPLAY=:0
ExecStart=/usr/bin/$BROWSER --kiosk http://localhost:8000/web --noerrdialogs --disable-infobars --disable-session-crashed-bubble
Restart=always

[Install]
WantedBy=graphical.target
EOF

sudo systemctl daemon-reload

sudo systemctl enable recall-server
sudo systemctl enable recall-player
sudo systemctl enable recall-kiosk

sudo systemctl start recall-server
sudo systemctl start recall-player

IP=$(hostname -I | awk '{print $1}')

echo ""
echo "================================="
echo " Recall installed successfully"
echo "================================="
echo ""
echo "Dashboard:"
echo "http://$IP:8000/web"
echo ""
echo "Update later with:"
echo "sudo /opt/recall/update.sh"
echo ""
