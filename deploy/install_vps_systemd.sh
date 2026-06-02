#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_USER="${SUDO_USER:-$(id -un)}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
DASHBOARD_HOST="${DASHBOARD_HOST:-127.0.0.1}"
DASHBOARD_PORT="${DASHBOARD_PORT:-8501}"

cd "$ROOT"

echo "[setup] Installing OS packages..."
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y python3 python3-venv python3-pip ca-certificates
fi

echo "[setup] Preparing folders..."
mkdir -p logs runtime

if [ ! -x ".venv/bin/python" ]; then
  echo "[setup] Creating virtualenv..."
  "$PYTHON_BIN" -m venv .venv
fi

echo "[setup] Installing Python dependencies..."
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt -r requirements_dashboard.txt

if [ ! -f ".env" ]; then
  echo "[setup] Creating .env from .env.example. Edit it before enabling live mode."
  cp .env.example .env
fi
chmod 600 .env

echo "[db] Preparing SQLite tables..."
.venv/bin/python scripts/launcher_prepare.py

echo "[systemd] Installing backend service..."
sudo tee /etc/systemd/system/crypto-ai-backend.service >/dev/null <<EOF
[Unit]
Description=Crypto AI Trader Backend
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$APP_USER
WorkingDirectory=$ROOT
Environment=PYTHONUNBUFFERED=1
ExecStart=$ROOT/.venv/bin/python $ROOT/main.py
Restart=always
RestartSec=10
KillSignal=SIGINT
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF

echo "[systemd] Installing dashboard service..."
sudo tee /etc/systemd/system/crypto-ai-dashboard.service >/dev/null <<EOF
[Unit]
Description=Crypto AI Trader Dashboard
After=network-online.target crypto-ai-backend.service
Wants=network-online.target

[Service]
Type=simple
User=$APP_USER
WorkingDirectory=$ROOT
Environment=PYTHONUNBUFFERED=1
ExecStart=$ROOT/.venv/bin/python -m streamlit run $ROOT/crypto_dashboard.py --server.address $DASHBOARD_HOST --server.port $DASHBOARD_PORT --server.headless true
Restart=always
RestartSec=10
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF

echo "[systemd] Enabling services..."
sudo systemctl daemon-reload
sudo systemctl enable crypto-ai-backend.service crypto-ai-dashboard.service

echo "[done] Installed."
echo "Start paper/live service with: sudo systemctl start crypto-ai-backend crypto-ai-dashboard"
echo "Dashboard host: $DASHBOARD_HOST:$DASHBOARD_PORT"
echo "Check status: ./deploy/status_vps.sh"
