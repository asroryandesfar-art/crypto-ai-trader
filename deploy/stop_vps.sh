#!/usr/bin/env bash
set -euo pipefail

sudo systemctl stop crypto-ai-backend.service crypto-ai-dashboard.service
echo "[ok] Services stopped."
