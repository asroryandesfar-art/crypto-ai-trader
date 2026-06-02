"""Switch .env between safe paper mode and explicit live mode."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from utils.runtime_safety import write_env_value


ENV_PATH = ROOT / ".env"


def ensure_env() -> None:
    if ENV_PATH.exists():
        return
    example = ROOT / ".env.example"
    if example.exists():
        ENV_PATH.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        ENV_PATH.write_text("", encoding="utf-8")


def set_paper() -> None:
    values = {
        "TRADING_MODE": "paper",
        "LIVE_TRADING": "false",
        "LIVE_TRADING_LOCKDOWN": "true",
        "LIVE_LOCKDOWN_REASON": "Paper mode is active. Run live preflight before enabling real orders.",
        "LIVE_ORDER_CONFIRMATION": "",
        "EMERGENCY_STOP": "false",
    }
    for key, value in values.items():
        write_env_value(ENV_PATH, key, value)


def set_live(accepted: bool) -> None:
    if not accepted:
        raise SystemExit("Refusing live mode without --accept-real-money-risk")

    values = {
        "TRADING_MODE": "live",
        "LIVE_TRADING": "true",
        "LIVE_TRADING_LOCKDOWN": "false",
        "LIVE_LOCKDOWN_REASON": "Live mode enabled after explicit confirmation.",
        "EMERGENCY_STOP": "false",
        "LIVE_ORDER_CONFIRMATION": "I_ACCEPT_REAL_MONEY_RISK",
    }
    for key, value in values.items():
        write_env_value(ENV_PATH, key, value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("paper", "live"))
    parser.add_argument("--accept-real-money-risk", action="store_true")
    args = parser.parse_args()

    ensure_env()
    if args.mode == "paper":
        set_paper()
        print("mode=paper")
    else:
        set_live(args.accept_real_money_risk)
        print("mode=live")
        print("live_order_confirmation=I_ACCEPT_REAL_MONEY_RISK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
