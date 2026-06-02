#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ ! -x ".venv/bin/python" ]; then
  echo "[error] Missing .venv. Run ./deploy/install_vps_systemd.sh first."
  exit 1
fi

echo "[safety] Running Binance live preflight. No orders are placed."
.venv/bin/python main.py --preflight-live

echo "[safety] Enabling explicit live mode in .env..."
.venv/bin/python scripts/set_trading_mode.py live --accept-real-money-risk

echo "[systemd] Restarting 24/7 backend and dashboard..."
sudo systemctl restart crypto-ai-backend.service crypto-ai-dashboard.service

echo "[ok] Live mode service restarted."
echo "Check status with: ./deploy/status_vps.sh"
