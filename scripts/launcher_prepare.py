"""Prepare the local database and safe environment before one-click startup."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from utils.runtime_safety import connect_sqlite, write_env_value


ENV_PATH = ROOT / ".env"
ENV_EXAMPLE_PATH = ROOT / ".env.example"
RUNTIME_DIR = ROOT / "runtime"
DEFAULT_DATABASE_URL = "sqlite:///./crypto_trader.db"


def read_env() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV_PATH.exists():
        return values
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def ensure_env_exists() -> None:
    if ENV_PATH.exists():
        return
    if ENV_EXAMPLE_PATH.exists():
        shutil.copyfile(ENV_EXAMPLE_PATH, ENV_PATH)
        return
    ENV_PATH.write_text(f"DATABASE_URL={DEFAULT_DATABASE_URL}\n", encoding="utf-8")


def force_paper_mode() -> None:
    safe_values = {
        "TRADING_MODE": "paper",
        "LIVE_TRADING": "false",
        "LIVE_TRADING_LOCKDOWN": "true",
        "LIVE_LOCKDOWN_REASON": "Use START_LIVE_TERMINAL.bat after live preflight to enable real orders.",
        "LIVE_ORDER_CONFIRMATION": "",
        "EMERGENCY_STOP": "false",
        "DATABASE_URL": DEFAULT_DATABASE_URL,
    }
    for key, value in safe_values.items():
        write_env_value(ENV_PATH, key, value)


def resolve_database_path(database_url: str) -> Path:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return ROOT / "crypto_trader.db"
    raw_path = database_url[len(prefix):]
    path = Path(raw_path)
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def ensure_dashboard_tables(db_path: Path, env: dict[str, str]) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now().isoformat(timespec="seconds")
    mode = env.get("TRADING_MODE", "paper")
    symbols = env.get("SYMBOLS", "BTC/USDT,ETH/USDT,SOL/USDT")
    live_trading = 1 if env.get("LIVE_TRADING", "false").lower() in {"1", "true", "yes", "on"} else 0

    with connect_sqlite(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS backend_status (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                status TEXT NOT NULL,
                mode TEXT NOT NULL,
                symbols TEXT NOT NULL,
                live_trading INTEGER NOT NULL,
                started_at TEXT,
                last_heartbeat TEXT NOT NULL,
                loop_count INTEGER NOT NULL DEFAULT 0,
                trades_executed INTEGER NOT NULL DEFAULT 0,
                total_pnl REAL NOT NULL DEFAULT 0,
                message TEXT NOT NULL DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS backend_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                agent TEXT NOT NULL,
                action TEXT NOT NULL,
                status TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS market_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                change_24h REAL NOT NULL DEFAULT 0,
                market_cap REAL NOT NULL DEFAULT 0,
                volume_24h REAL NOT NULL DEFAULT 0,
                source TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS trading_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL,
                confidence INTEGER NOT NULL,
                price REAL NOT NULL,
                reason TEXT NOT NULL,
                ai_summary TEXT NOT NULL DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS paper_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_price REAL NOT NULL,
                current_price REAL NOT NULL,
                quantity REAL NOT NULL,
                leverage REAL NOT NULL DEFAULT 1,
                pnl REAL NOT NULL DEFAULT 0,
                pnl_percent REAL NOT NULL DEFAULT 0,
                opened_at TEXT NOT NULL,
                closed_at TEXT,
                status TEXT NOT NULL,
                reason TEXT NOT NULL DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS live_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                exchange_symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_price REAL NOT NULL,
                current_price REAL NOT NULL,
                quantity REAL NOT NULL,
                notional_usdt REAL NOT NULL,
                leverage REAL NOT NULL DEFAULT 1,
                stop_loss_price REAL,
                take_profit_price REAL,
                entry_order_id TEXT NOT NULL DEFAULT '',
                stop_order_id TEXT NOT NULL DEFAULT '',
                take_profit_order_id TEXT NOT NULL DEFAULT '',
                close_order_id TEXT NOT NULL DEFAULT '',
                pnl REAL NOT NULL DEFAULT 0,
                pnl_percent REAL NOT NULL DEFAULT 0,
                opened_at TEXT NOT NULL,
                closed_at TEXT,
                status TEXT NOT NULL,
                reason TEXT NOT NULL DEFAULT ''
            )
        """)
        row = conn.execute(
            "SELECT status, started_at, last_heartbeat, loop_count, trades_executed, total_pnl, message "
            "FROM backend_status WHERE id = 1"
        ).fetchone()
        fresh_running = False
        if row and row[0] == "running":
            try:
                fresh_running = (datetime.now() - datetime.fromisoformat(row[2])).total_seconds() <= 120
            except (TypeError, ValueError):
                fresh_running = False

        if fresh_running:
            conn.execute(
                """
                UPDATE backend_status
                SET mode = ?, symbols = ?, live_trading = ?
                WHERE id = 1
                """,
                (mode, symbols, live_trading),
            )
        else:
            conn.execute(
                """
                INSERT INTO backend_status (
                    id, status, mode, symbols, live_trading, started_at,
                    last_heartbeat, loop_count, trades_executed, total_pnl, message
                )
                VALUES (1, 'offline', ?, ?, ?, NULL, ?, 0, 0, 0, 'Launcher prepared database')
                ON CONFLICT(id) DO UPDATE SET
                    status = 'offline',
                    mode = excluded.mode,
                    symbols = excluded.symbols,
                    live_trading = excluded.live_trading,
                    started_at = NULL,
                    last_heartbeat = excluded.last_heartbeat,
                    loop_count = 0,
                    message = excluded.message
                """,
                (mode, symbols, live_trading, now),
            )
        conn.execute(
            """
            INSERT INTO backend_events (timestamp, agent, action, status)
            VALUES (?, 'Launcher', 'Database checked and dashboard tables are ready', 'OK')
            """,
            (now,),
        )
        conn.commit()


def write_launcher_status(db_path: Path, env: dict[str, str]) -> None:
    RUNTIME_DIR.mkdir(exist_ok=True)
    status = {
        "prepared_at": datetime.now().isoformat(timespec="seconds"),
        "database_path": str(db_path),
        "database_exists": db_path.exists(),
        "database_url": env.get("DATABASE_URL", DEFAULT_DATABASE_URL),
        "dashboard_url": "http://127.0.0.1:8501",
        "mode": env.get("TRADING_MODE", "paper"),
        "live_trading": env.get("LIVE_TRADING", "false"),
    }
    (RUNTIME_DIR / "launcher_status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper", action="store_true", help="Force safe paper mode before starting services.")
    args = parser.parse_args()

    ensure_env_exists()
    if args.paper:
        force_paper_mode()

    env = read_env()
    database_url = env.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    db_path = resolve_database_path(database_url)
    ensure_dashboard_tables(db_path, env)
    write_launcher_status(db_path, env)

    print(f"database_path={db_path}")
    print(f"dashboard_url=http://127.0.0.1:8501")
    print(f"mode={env.get('TRADING_MODE', 'paper')}")
    print(f"live_trading={env.get('LIVE_TRADING', 'false')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
