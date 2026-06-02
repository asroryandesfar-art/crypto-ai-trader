"""
Main entry point for the AI multi-agent crypto trading bot.
Orchestrates all components and manages the trading loop.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Optional
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import ENV_PATH, settings
from services.coingecko_service import CoinGeckoService
from services.groq_service import GroqService
from services.live_exchange import BinanceFuturesLiveExecutor, LiveExecutionError
from utils.runtime_safety import connect_sqlite, install_secret_redaction

# Setup logging
def setup_logging(name: str, level: str = "INFO") -> logging.Logger:
    """Setup logger with file and console handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(level.upper())

    if logger.handlers:
        return logger

    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_formatter = logging.Formatter(
        fmt='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level.upper())
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler
    logs_dir = PROJECT_ROOT / "logs"
    logs_dir.mkdir(exist_ok=True)
    log_file = logs_dir / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(level.upper())
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)

    return logger

logger = setup_logging("main", settings.log_level)
install_secret_redaction(
    logger,
    (
        settings.groq_api_key,
        settings.binance_api_key or "",
        settings.binance_secret_key or "",
        settings.telegram_bot_token or "",
    ),
)

BACKEND_LOCK_HANDLE = None


def acquire_backend_lock() -> bool:
    """Prevent more than one backend trading loop per workspace."""
    global BACKEND_LOCK_HANDLE
    runtime_dir = PROJECT_ROOT / "runtime"
    runtime_dir.mkdir(exist_ok=True)
    lock_path = runtime_dir / "backend.lock"
    BACKEND_LOCK_HANDLE = lock_path.open("a+")
    try:
        BACKEND_LOCK_HANDLE.seek(0)
        if sys.platform == "win32":
            import msvcrt

            msvcrt.locking(BACKEND_LOCK_HANDLE.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(BACKEND_LOCK_HANDLE.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        BACKEND_LOCK_HANDLE.close()
        BACKEND_LOCK_HANDLE = None
        return False
    BACKEND_LOCK_HANDLE.seek(0)
    BACKEND_LOCK_HANDLE.truncate()
    BACKEND_LOCK_HANDLE.write(str(os.getpid()))
    BACKEND_LOCK_HANDLE.flush()
    return True


def env_flag_enabled(name: str) -> Optional[bool]:
    """Read a boolean flag directly from .env so emergency stop can change while running."""
    try:
        if not ENV_PATH.exists():
            return None
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            if key.strip() == name:
                return value.strip().lower() in {"1", "true", "yes", "on"}
    except Exception as exc:
        logger.warning("Could not read %s from .env: %s", name, exc)
    return None


def emergency_stop_requested(config) -> bool:
    live_env_flag = env_flag_enabled("EMERGENCY_STOP")
    return config.emergency_stop or live_env_flag is True


def resolve_sqlite_path(database_url: str) -> Path:
    """Resolve sqlite DATABASE_URL into the DB file shared with the dashboard."""
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return PROJECT_ROOT / "crypto_trader.db"

    raw_path = database_url[len(prefix):]
    path = Path(raw_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def ensure_dashboard_tables(db_path: Path) -> None:
    """Create lightweight status/event tables consumed by Streamlit."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
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
        conn.commit()


def publish_dashboard_status(
    db_path: Path,
    config,
    status: str,
    start_time: Optional[datetime] = None,
    loop_count: int = 0,
    trades_executed: int = 0,
    total_pnl: float = 0.0,
    message: str = "",
) -> None:
    """Publish backend heartbeat/status for the dashboard."""
    now = datetime.now().isoformat(timespec="seconds")
    started_at = start_time.isoformat(timespec="seconds") if start_time else ""
    payload = (
        1,
        status,
        config.trading_mode,
        json.dumps(config.get_symbols_list()),
        1 if config.is_live_mode() else 0,
        started_at,
        now,
        loop_count,
        trades_executed,
        total_pnl,
        message,
    )
    with connect_sqlite(db_path) as conn:
        conn.execute("""
            INSERT INTO backend_status (
                id, status, mode, symbols, live_trading, started_at,
                last_heartbeat, loop_count, trades_executed, total_pnl, message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                status = excluded.status,
                mode = excluded.mode,
                symbols = excluded.symbols,
                live_trading = excluded.live_trading,
                started_at = excluded.started_at,
                last_heartbeat = excluded.last_heartbeat,
                loop_count = excluded.loop_count,
                trades_executed = excluded.trades_executed,
                total_pnl = excluded.total_pnl,
                message = excluded.message
        """, payload)
        conn.commit()


def publish_dashboard_event(db_path: Path, agent: str, action: str, status: str = "OK") -> None:
    """Append a short backend event visible in the dashboard logs page."""
    with connect_sqlite(db_path) as conn:
        conn.execute(
            "INSERT INTO backend_events (timestamp, agent, action, status) VALUES (?, ?, ?, ?)",
            (datetime.now().isoformat(timespec="seconds"), agent, action, status),
        )
        conn.execute("""
            DELETE FROM backend_events
            WHERE id NOT IN (
                SELECT id FROM backend_events ORDER BY id DESC LIMIT 200
            )
        """)
        conn.commit()


def store_market_snapshot(db_path: Path, symbol: str, market: dict) -> None:
    with connect_sqlite(db_path) as conn:
        conn.execute(
            """
            INSERT INTO market_snapshots (
                timestamp, symbol, price, change_24h, market_cap, volume_24h, source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().isoformat(timespec="seconds"),
                symbol,
                market["price"],
                market.get("change_24h", 0),
                market.get("market_cap", 0),
                market.get("volume_24h", 0),
                market.get("source", "unknown"),
            ),
        )
        conn.commit()


def store_trading_signal(db_path: Path, symbol: str, signal: dict, price: float) -> None:
    with connect_sqlite(db_path) as conn:
        conn.execute(
            """
            INSERT INTO trading_signals (
                timestamp, symbol, action, confidence, price, reason, ai_summary
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().isoformat(timespec="seconds"),
                symbol,
                signal["action"],
                int(signal["confidence"]),
                price,
                signal.get("reason", ""),
                signal.get("raw", ""),
            ),
        )
        conn.commit()


def refresh_open_position_prices(db_path: Path, prices: dict) -> None:
    with connect_sqlite(db_path) as conn:
        rows = conn.execute(
            "SELECT id, symbol, side, entry_price, quantity FROM paper_positions WHERE status = 'OPEN'"
        ).fetchall()
        for position_id, symbol, side, entry_price, quantity in rows:
            market = prices.get(symbol)
            if not market:
                continue
            current_price = market["price"]
            direction = 1 if side == "BUY" else -1
            pnl = (current_price - entry_price) * quantity * direction
            pnl_percent = ((current_price - entry_price) / entry_price) * 100 * direction if entry_price else 0
            conn.execute(
                """
                UPDATE paper_positions
                SET current_price = ?, pnl = ?, pnl_percent = ?
                WHERE id = ?
                """,
                (current_price, pnl, pnl_percent, position_id),
            )
        live_rows = conn.execute(
            "SELECT id, symbol, side, entry_price, quantity FROM live_positions WHERE status = 'OPEN'"
        ).fetchall()
        for position_id, symbol, side, entry_price, quantity in live_rows:
            market = prices.get(symbol)
            if not market:
                continue
            current_price = market["price"]
            direction = 1 if side == "BUY" else -1
            pnl = (current_price - entry_price) * quantity * direction
            pnl_percent = ((current_price - entry_price) / entry_price) * 100 * direction if entry_price else 0
            conn.execute(
                """
                UPDATE live_positions
                SET current_price = ?, pnl = ?, pnl_percent = ?
                WHERE id = ?
                """,
                (current_price, pnl, pnl_percent, position_id),
            )
        conn.commit()


def paper_execute_signal(db_path: Path, config, symbol: str, signal: dict, price: float) -> Optional[str]:
    """Open/close simulated positions. Live exchange execution is intentionally gated."""
    action = signal["action"]
    confidence = int(signal["confidence"])
    if action == "HOLD" or confidence < config.confidence_threshold:
        return None

    with connect_sqlite(db_path) as conn:
        open_count = conn.execute(
            "SELECT COUNT(*) FROM paper_positions WHERE status = 'OPEN'"
        ).fetchone()[0]
        existing = conn.execute(
            "SELECT id, side, entry_price, quantity FROM paper_positions WHERE status = 'OPEN' AND symbol = ?",
            (symbol,),
        ).fetchone()

        if action == "BUY":
            if existing:
                return "Skipped BUY: position already open"
            if open_count >= config.max_open_positions:
                return "Skipped BUY: max open positions reached"
            notional = 10000 * (config.max_risk_per_trade / 100)
            quantity = round(notional / price, 8) if price else 0
            conn.execute(
                """
                INSERT INTO paper_positions (
                    symbol, side, entry_price, current_price, quantity, leverage,
                    pnl, pnl_percent, opened_at, status, reason
                )
                VALUES (?, ?, ?, ?, ?, ?, 0, 0, ?, 'OPEN', ?)
                """,
                (
                    symbol,
                    "BUY",
                    price,
                    price,
                    quantity,
                    min(config.max_leverage, 1),
                    datetime.now().isoformat(timespec="seconds"),
                    signal.get("reason", ""),
                ),
            )
            conn.commit()
            return f"Opened paper BUY {symbol} qty={quantity}"

        if action == "SELL" and existing:
            position_id, side, entry_price, quantity = existing
            direction = 1 if side == "BUY" else -1
            pnl = (price - entry_price) * quantity * direction
            pnl_percent = ((price - entry_price) / entry_price) * 100 * direction if entry_price else 0
            conn.execute(
                """
                UPDATE paper_positions
                SET current_price = ?, pnl = ?, pnl_percent = ?, closed_at = ?,
                    status = 'CLOSED', reason = ?
                WHERE id = ?
                """,
                (
                    price,
                    pnl,
                    pnl_percent,
                    datetime.now().isoformat(timespec="seconds"),
                    signal.get("reason", ""),
                    position_id,
                ),
            )
            conn.commit()
            return f"Closed paper position {symbol} pnl={pnl:.2f}"

    return None


def get_live_open_position(db_path: Path, symbol: str):
    with connect_sqlite(db_path) as conn:
        return conn.execute(
            """
            SELECT id, entry_price, quantity, stop_order_id, take_profit_order_id
            FROM live_positions
            WHERE status = 'OPEN' AND symbol = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (symbol,),
        ).fetchone()


def get_live_open_count(db_path: Path) -> int:
    with connect_sqlite(db_path) as conn:
        return int(
            conn.execute("SELECT COUNT(*) FROM live_positions WHERE status = 'OPEN'").fetchone()[0]
        )


def get_today_live_loss_usdt(db_path: Path) -> float:
    today = datetime.now().date().isoformat()
    with connect_sqlite(db_path) as conn:
        loss = conn.execute(
            """
            SELECT COALESCE(SUM(CASE WHEN pnl < 0 THEN ABS(pnl) ELSE 0 END), 0)
            FROM live_positions
            WHERE status = 'CLOSED' AND closed_at LIKE ?
            """,
            (f"{today}%",),
        ).fetchone()[0]
    return float(loss or 0)


def record_live_open_position(db_path: Path, result, leverage: float, reason: str) -> None:
    with connect_sqlite(db_path) as conn:
        conn.execute(
            """
            INSERT INTO live_positions (
                symbol, exchange_symbol, side, entry_price, current_price, quantity,
                notional_usdt, leverage, stop_loss_price, take_profit_price,
                entry_order_id, stop_order_id, take_profit_order_id, opened_at,
                status, reason
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?)
            """,
            (
                result.symbol,
                result.exchange_symbol,
                result.side,
                result.entry_price,
                result.entry_price,
                result.quantity,
                result.notional_usdt,
                leverage,
                result.stop_loss_price,
                result.take_profit_price,
                result.entry_order_id,
                result.stop_order_id,
                result.take_profit_order_id,
                datetime.now().isoformat(timespec="seconds"),
                reason,
            ),
        )
        conn.commit()


def record_live_close_position(db_path: Path, position_id: int, result, reason: str) -> None:
    pnl_percent = 0.0
    with connect_sqlite(db_path) as conn:
        row = conn.execute(
            "SELECT entry_price FROM live_positions WHERE id = ?",
            (position_id,),
        ).fetchone()
        if row and row[0]:
            pnl_percent = ((result.entry_price - float(row[0])) / float(row[0])) * 100
        conn.execute(
            """
            UPDATE live_positions
            SET current_price = ?, pnl = ?, pnl_percent = ?, close_order_id = ?,
                closed_at = ?, status = 'CLOSED', reason = ?
            WHERE id = ?
            """,
            (
                result.entry_price,
                result.realized_pnl,
                pnl_percent,
                result.close_order_id,
                datetime.now().isoformat(timespec="seconds"),
                reason,
                position_id,
            ),
        )
        conn.commit()


async def live_execute_signal(
    db_path: Path,
    live_executor: Optional[BinanceFuturesLiveExecutor],
    config,
    symbol: str,
    signal: dict,
    price: float,
) -> Optional[str]:
    """Execute a live signal through the gated futures executor."""
    if live_executor is None:
        return "Skipped live execution: exchange executor is not initialized"

    action = signal["action"]
    confidence = int(signal["confidence"])
    if action == "HOLD" or confidence < config.confidence_threshold:
        return None

    if emergency_stop_requested(config):
        return "Skipped live execution: emergency stop is active"

    try:
        if action == "BUY":
            if get_live_open_position(db_path, symbol):
                return "Skipped LIVE BUY: position already open"
            if get_live_open_count(db_path) >= config.max_open_positions:
                return "Skipped LIVE BUY: max open positions reached"

            snapshot = await asyncio.to_thread(live_executor.fetch_account_snapshot)
            loss_limit = snapshot.total_usdt * (config.daily_max_loss / 100)
            today_loss = get_today_live_loss_usdt(db_path)
            if loss_limit > 0 and today_loss >= loss_limit:
                return f"Blocked LIVE BUY: daily loss guard hit ({today_loss:.2f}/{loss_limit:.2f} USDT)"

            result = await asyncio.to_thread(live_executor.open_long, symbol, price)
            try:
                record_live_open_position(db_path, result, config.max_leverage, signal.get("reason", ""))
            except Exception as db_exc:
                logger.critical(
                    "Live BUY opened but DB persistence failed for %s; closing position immediately: %s",
                    symbol,
                    db_exc,
                )
                await asyncio.to_thread(
                    live_executor.close_long,
                    symbol,
                    result.quantity,
                    result.entry_price,
                    result.stop_order_id,
                    result.take_profit_order_id,
                )
                return f"Closed emergency LIVE BUY {symbol}: DB persistence failed"
            return (
                f"Opened LIVE BUY {symbol} qty={result.quantity} "
                f"notional={result.notional_usdt:.2f} stop={result.stop_loss_price}"
            )

        if action == "SELL":
            existing = get_live_open_position(db_path, symbol)
            if not existing:
                return "Skipped LIVE SELL: no open long position"
            position_id, entry_price, quantity, stop_order_id, take_profit_order_id = existing
            result = await asyncio.to_thread(
                live_executor.close_long,
                symbol,
                quantity,
                entry_price,
                stop_order_id,
                take_profit_order_id,
            )
            record_live_close_position(db_path, position_id, result, signal.get("reason", ""))
            return f"Closed LIVE position {symbol} pnl={result.realized_pnl:.2f} USDT"

    except LiveExecutionError as exc:
        logger.error("Live execution blocked/failed for %s: %s", symbol, exc)
        return f"Live execution blocked/failed for {symbol}: {exc}"

    return None


class CryptoTradingBot:
    """
    Main trading bot orchestrator.
    Coordinates all agents and manages the trading loop.
    """

    def __init__(self):
        """Initialize the trading bot."""
        self.config = settings
        self.running = False
        self.start_time = None
        self.trades_executed = 0
        self.total_pnl = 0.0
        self.db_path = resolve_sqlite_path(self.config.database_url)
        self.market_service = CoinGeckoService()
        self.groq_service = GroqService(self.config.groq_api_key, self.config.groq_model)
        self.live_executor: Optional[BinanceFuturesLiveExecutor] = None

        logger.info("=" * 60)
        logger.info("CRYPTO AI TRADING BOT INITIALIZED")
        logger.info("=" * 60)
        logger.info(f"Mode: {self.config.trading_mode.upper()}")
        logger.info(f"Symbols: {self.config.get_symbols_list()}")
        logger.info(f"Max Risk per Trade: {self.config.max_risk_per_trade}%")
        logger.info(f"Daily Max Loss: {self.config.daily_max_loss}%")
        logger.info(f"Confidence Threshold: {self.config.confidence_threshold}")
        logger.info(f"Max Open Positions: {self.config.max_open_positions}")
        logger.info(f"Max Live Order: {self.config.max_live_order_usdt} USDT")
        ensure_dashboard_tables(self.db_path)
        publish_dashboard_status(self.db_path, self.config, "starting", message="Backend process initialized")

    def validate_startup(self) -> bool:
        """
        Validate bot can start safely.
        
        Returns:
            bool: True if safe to start, False otherwise
        """
        logger.info("\nValidating startup requirements...")

        # Check emergency stop
        if emergency_stop_requested(self.config):
            logger.error("ERROR: EMERGENCY STOP is active - cannot start trading")
            return False
        logger.info("OK: Emergency stop check passed")

        # Check live mode safety
        if self.config.is_live_mode():
            logger.warning("\nWARNING: LIVE TRADING MODE ENABLED")
            logger.warning("This will execute REAL trades with REAL money")

            if not self.config.validate_live_mode():
                logger.error("ERROR: Live trading validation failed")
                return False
            logger.info("OK: Live trading requirements validated")
        else:
            logger.info("OK: Running in PAPER/BACKTEST mode (no real trades)")

        # Check API keys
        if not self.config.groq_api_key:
            logger.error("ERROR: GROQ_API_KEY is missing")
            return False
        logger.info("OK: Groq API key found")

        if self.config.is_live_mode():
            if not self.config.binance_api_key or not self.config.binance_secret_key:
                logger.error("ERROR: Binance API keys are missing for live trading")
                return False
            logger.info("OK: Binance API keys found")
            logger.info("OK: Live order confirmation found")

        # Check configuration validity
        if self.config.confidence_threshold < 0 or self.config.confidence_threshold > 100:
            logger.error("ERROR: Invalid confidence threshold")
            return False
        logger.info("OK: Configuration validation passed")

        return True

    async def initialize_services(self) -> bool:
        """
        Initialize all services and agents.
        
        Returns:
            bool: True if all services initialized successfully
        """
        logger.info("\nInitializing services...")

        try:
            if self.config.is_live_mode():
                self.live_executor = BinanceFuturesLiveExecutor(
                    api_key=self.config.binance_api_key or "",
                    secret_key=self.config.binance_secret_key or "",
                    leverage=self.config.max_leverage,
                    max_order_usdt=self.config.max_live_order_usdt,
                    min_order_usdt=self.config.min_live_order_usdt,
                    max_risk_per_trade=self.config.max_risk_per_trade,
                    stop_loss_pct=self.config.live_stop_loss_pct,
                    take_profit_pct=self.config.live_take_profit_pct,
                    account_type=self.config.binance_account_type,
                )
                snapshot = await asyncio.to_thread(
                    self.live_executor.connect,
                    self.config.get_symbols_list(),
                )
                open_exchange_positions = await asyncio.to_thread(
                    self.live_executor.fetch_open_positions,
                    self.config.get_symbols_list(),
                )
                if open_exchange_positions and get_live_open_count(self.db_path) == 0:
                    logger.critical(
                        "Exchange has open positions that are not recorded in local DB; live trading startup blocked"
                    )
                    return False
                publish_dashboard_event(
                    self.db_path,
                    "ExecutionAgent",
                    f"Live Binance {self.config.binance_account_type} preflight OK: free USDT {snapshot.free_usdt:.2f}",
                )
            logger.info("OK: Services initialization complete")
            return True

        except Exception as e:
            logger.error(f"ERROR: Failed to initialize services: {e}")
            return False

    def technical_fallback_signal(self, symbol: str, market: dict) -> dict:
        """Simple local signal used when AI is unavailable or cautious."""
        change = market.get("change_24h", 0)
        if change >= 2.0:
            return {
                "action": "BUY",
                "confidence": min(85, int(60 + change * 5)),
                "reason": f"24h momentum is positive at {change:.2f}%.",
                "raw": "technical_fallback",
            }
        if change <= -2.5:
            return {
                "action": "SELL",
                "confidence": min(85, int(60 + abs(change) * 4)),
                "reason": f"24h momentum is negative at {change:.2f}%.",
                "raw": "technical_fallback",
            }
        return {
            "action": "HOLD",
            "confidence": 55,
            "reason": f"24h change {change:.2f}% is not strong enough.",
            "raw": "technical_fallback",
        }

    async def analyze_symbol(self, symbol: str, market: dict) -> dict:
        """Combine market data and Groq AI into a final signal."""
        fallback = self.technical_fallback_signal(symbol, market)
        payload = {
            "symbol": symbol,
            "price": market["price"],
            "change_24h": market.get("change_24h", 0),
            "volume_24h": market.get("volume_24h", 0),
            "technical_fallback": fallback,
            "trading_mode": self.config.trading_mode,
            "confidence_threshold": self.config.confidence_threshold,
        }
        try:
            ai_signal = await asyncio.wait_for(self.groq_service.trading_decision(payload), timeout=30)
        except asyncio.TimeoutError:
            publish_dashboard_event(self.db_path, "Groq", f"{symbol}: AI timeout, using technical fallback", "WARNING")
            ai_signal = None
        if not ai_signal:
            return fallback

        if ai_signal["confidence"] < self.config.confidence_threshold and fallback["action"] == "HOLD":
            ai_signal["action"] = "HOLD"
        return ai_signal

    async def run_market_cycle(self, loop_count: int) -> None:
        """Fetch prices, produce AI signals, and simulate paper execution."""
        symbols = self.config.get_symbols_list()
        publish_dashboard_status(
            self.db_path,
            self.config,
            "running",
            start_time=self.start_time,
            loop_count=loop_count,
            trades_executed=self.trades_executed,
            total_pnl=self.total_pnl,
            message="Fetching market data",
        )
        try:
            prices = await asyncio.wait_for(
                self.market_service.fetch_prices(symbols, self.config.max_symbols_per_cycle),
                timeout=35,
            )
        except asyncio.TimeoutError:
            publish_dashboard_event(self.db_path, "MarketAnalyst", "Market data timeout", "WARNING")
            prices = {}
        if not prices:
            publish_dashboard_event(self.db_path, "MarketAnalyst", "No market data returned", "WARNING")
            publish_dashboard_status(
                self.db_path,
                self.config,
                "running",
                start_time=self.start_time,
                loop_count=loop_count,
                message="No market data returned",
            )
            return

        refresh_open_position_prices(self.db_path, prices)

        for symbol, market in prices.items():
            store_market_snapshot(self.db_path, symbol, market)
            signal = await self.analyze_symbol(symbol, market)
            store_trading_signal(self.db_path, symbol, signal, market["price"])
            publish_dashboard_event(
                self.db_path,
                "SupervisorAgent",
                f"{symbol}: {signal['action']} {signal['confidence']}%",
            )

            if self.config.is_live_mode():
                execution = await live_execute_signal(
                    self.db_path,
                    self.live_executor,
                    self.config,
                    symbol,
                    signal,
                    market["price"],
                )
            else:
                execution = paper_execute_signal(self.db_path, self.config, symbol, signal, market["price"])
            if execution:
                if execution.startswith(("Opened ", "Closed ")):
                    self.trades_executed += 1
                publish_dashboard_event(self.db_path, "ExecutionAgent", execution)

    async def run_trading_loop(self):
        """
        Main trading loop.
        Runs indefinitely until stopped.
        """
        logger.info("\n" + "=" * 60)
        logger.info("STARTING TRADING LOOP")
        logger.info("=" * 60 + "\n")

        self.start_time = datetime.now()
        self.running = True
        loop_count = 0
        publish_dashboard_status(
            self.db_path,
            self.config,
            "running",
            start_time=self.start_time,
            loop_count=loop_count,
            trades_executed=self.trades_executed,
            total_pnl=self.total_pnl,
            message="Trading loop started",
        )
        publish_dashboard_event(self.db_path, "Backend", "Trading loop started")

        try:
            while self.running:
                loop_count += 1
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                try:
                    logger.info(f"\n[Loop {loop_count}] Starting at {current_time}")
                    logger.info("-" * 60)

                    # Check emergency stop
                    if emergency_stop_requested(self.config):
                        logger.error("EMERGENCY STOP triggered - halting all trades")
                        self.running = False
                        break

                    # TODO: Implement trading loop logic
                    # 1. Fetch market data
                    # 2. Run market analysis
                    # 3. Get news and sentiment
                    # 4. Track whale activity
                    # 5. Check liquidations
                    # 6. Run supervisor agent
                    # 7. Execute trades if signal
                    # 8. Manage risk
                    # 9. Log results
                    # 10. Update dashboard
                    await self.run_market_cycle(loop_count)

                    logger.info("Trading loop cycle completed")
                    publish_dashboard_status(
                        self.db_path,
                        self.config,
                        "running",
                        start_time=self.start_time,
                        loop_count=loop_count,
                        trades_executed=self.trades_executed,
                        total_pnl=self.total_pnl,
                        message="Last cycle completed",
                    )
                    publish_dashboard_event(self.db_path, "SupervisorAgent", f"Loop {loop_count} completed")
                    logger.info("-" * 60)

                    # Wait before next iteration
                    await asyncio.sleep(60)  # Run every 60 seconds

                except KeyboardInterrupt:
                    logger.info("\nKeyboard interrupt detected - shutting down gracefully")
                    self.running = False
                    break

                except Exception as e:
                    logger.error(f"Error in trading loop: {e}", exc_info=True)
                    await asyncio.sleep(30)  # Wait 30 seconds before retry

        except Exception as e:
            logger.error(f"Critical error in trading loop: {e}", exc_info=True)
        finally:
            await self.shutdown()

    async def shutdown(self):
        """
        Gracefully shutdown the bot.
        Close all connections and cleanup.
        """
        logger.info("\n" + "=" * 60)
        logger.info("SHUTTING DOWN TRADING BOT")
        logger.info("=" * 60)

        self.running = False

        try:
            # Close all open positions in paper mode if needed
            logger.info("Closing connections...")

            uptime = datetime.now() - self.start_time if self.start_time else None
            logger.info(f"\nBot Statistics:")
            logger.info(f"  Uptime: {uptime}")
            logger.info(f"  Trades Executed: {self.trades_executed}")
            logger.info(f"  Total P&L: ${self.total_pnl:,.2f}")
            publish_dashboard_status(
                self.db_path,
                self.config,
                "stopped",
                start_time=self.start_time,
                trades_executed=self.trades_executed,
                total_pnl=self.total_pnl,
                message="Backend shutdown complete",
            )
            publish_dashboard_event(self.db_path, "Backend", "Backend shutdown complete")

            logger.info("\nOK: Bot shutdown complete")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)

    async def run(self):
        """
        Main run method.
        Validates startup and starts trading loop.
        """
        # Validate startup
        if not self.validate_startup():
            logger.error("\nERROR: Startup validation failed - exiting")
            publish_dashboard_status(self.db_path, self.config, "blocked", message="Startup validation failed")
            publish_dashboard_event(self.db_path, "Backend", "Startup validation failed", "ERROR")
            return

        # Initialize services
        if not await self.initialize_services():
            logger.error("\nERROR: Service initialization failed - exiting")
            publish_dashboard_status(self.db_path, self.config, "error", message="Service initialization failed")
            publish_dashboard_event(self.db_path, "Backend", "Service initialization failed", "ERROR")
            return

        # Start trading loop
        try:
            await self.run_trading_loop()
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)


def main():
    """
    Entry point for the application.
    """
    try:
        if not acquire_backend_lock():
            logger.error("Another backend instance is already running; exiting duplicate process")
            return
        # Create bot instance
        bot = CryptoTradingBot()

        # Run bot
        asyncio.run(bot.run())

    except KeyboardInterrupt:
        logger.info("\nKeyboard interrupt - exiting")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


def run_live_preflight() -> int:
    """Validate Binance Futures connectivity without placing orders."""
    if not settings.binance_api_key or not settings.binance_secret_key:
        print("LIVE PREFLIGHT FAILED: Binance API keys are missing")
        return 1

    try:
        executor = BinanceFuturesLiveExecutor(
            api_key=settings.binance_api_key or "",
            secret_key=settings.binance_secret_key or "",
            leverage=settings.max_leverage,
            max_order_usdt=settings.max_live_order_usdt,
            min_order_usdt=settings.min_live_order_usdt,
            max_risk_per_trade=settings.max_risk_per_trade,
            stop_loss_pct=settings.live_stop_loss_pct,
            take_profit_pct=settings.live_take_profit_pct,
            account_type=settings.binance_account_type,
        )
        snapshot = executor.connect(settings.get_symbols_list(), prepare_exchange=False)
    except Exception as exc:
        print(f"LIVE PREFLIGHT FAILED: {exc}")
        return 1

    print("LIVE PREFLIGHT OK")
    print(f"Mode configured: {settings.trading_mode}")
    print(f"Binance account type: {settings.binance_account_type}")
    print(f"Live flag: {settings.live_trading}")
    print(f"Symbols: {', '.join(settings.get_symbols_list())}")
    print(f"USDT free: {snapshot.free_usdt:.2f}")
    print(f"USDT total: {snapshot.total_usdt:.2f}")
    print(f"Max live order: {settings.max_live_order_usdt:.2f} USDT")
    print(f"Leverage cap: {settings.max_leverage}x")
    print("No orders were placed.")
    return 0


if __name__ == "__main__":
    if "--preflight-live" in sys.argv:
        sys.exit(run_live_preflight())
    main()
