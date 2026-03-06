
#!/usr/bin/env bash
set -e

INSTALL_DIR="/opt/recall"

echo "Removing Recall..."

sudo systemctl stop recall-server || true
sudo systemctl stop recall-player || true
sudo systemctl stop recall-kiosk || true

sudo systemctl disable recall-server || true
sudo systemctl disable recall-player || true
sudo systemctl disable recall-kiosk || true

sudo rm -f /etc/systemd/system/recall-server.service
sudo rm -f /etc/systemd/system/recall-player.service
sudo rm -f /etc/systemd/system/recall-kiosk.service

sudo systemctl daemon-reload

sudo rm -rf $INSTALL_DIR

echo "Recall removed."
