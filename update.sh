
#!/usr/bin/env bash
set -e

INSTALL_DIR="/opt/recall"

echo "Updating Recall..."

cd $INSTALL_DIR
git pull

source venv/bin/activate
pip install -r requirements.txt || true

sudo systemctl restart recall-server
sudo systemctl restart recall-player

echo "Update complete."
