#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "[systemd]"
systemctl --no-pager --full status crypto-ai-backend.service crypto-ai-dashboard.service || true

echo
echo "[recent backend logs]"
journalctl -u crypto-ai-backend.service -n 80 --no-pager || true

echo
echo "[recent dashboard logs]"
journalctl -u crypto-ai-dashboard.service -n 50 --no-pager || true
