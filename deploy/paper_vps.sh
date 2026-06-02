#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ ! -x ".venv/bin/python" ]; then
  echo "[error] Missing .venv. Run ./deploy/install_vps_systemd.sh first."
  exit 1
fi

.venv/bin/python scripts/set_trading_mode.py paper
sudo systemctl restart crypto-ai-backend.service crypto-ai-dashboard.service

echo "[ok] Paper mode service restarted."
