
#!/usr/bin/env bash
set -e

echo "Updating Recall..."

cd /opt/recall

git pull

source venv/bin/activate

pip install --upgrade fastapi uvicorn psutil requests python-multipart

sudo systemctl restart recall-server
sudo systemctl restart recall-player

echo "Update complete."
