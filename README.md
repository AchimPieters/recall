
# Recall

Lightweight Digital Signage platform for Raspberry Pi.

## Install

Run:

bash <(curl -sL https://raw.githubusercontent.com/AchimPieters/recall/main/install.sh)

Open:

http://<pi-ip>:8000/web

## Update

sudo /opt/recall/update.sh

## Uninstall

sudo /opt/recall/uninstall.sh

## Local UI Development

Install Flask:

pip install flask

Start dev server:

python tools/server.py

Open:

http://localhost:8080
