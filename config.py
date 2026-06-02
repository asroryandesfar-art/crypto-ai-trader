"""
Configuration module for crypto trading bot.
Loads and validates environment variables.
"""

import os
import re
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv
from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import logging

# Load environment variables
ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(ENV_PATH)

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Provides type-safe configuration with validation.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # ============================================
    # API Keys (CRITICAL: Never hardcode)
    # ============================================
    groq_api_key: str = Field(..., alias="GROQ_API_KEY", repr=False)
    groq_model: str = Field(default="llama-3.1-8b-instant", alias="GROQ_MODEL")
    binance_api_key: Optional[str] = Field(None, alias="BINANCE_API_KEY", repr=False)
    binance_secret_key: Optional[str] = Field(None, alias="BINANCE_SECRET_KEY", repr=False)

    # ============================================
    # Trading Mode Configuration
    # ============================================
    live_trading: bool = Field(default=False, alias="LIVE_TRADING")
    trading_mode: str = Field(default="paper", alias="TRADING_MODE")
    live_trading_lockdown: bool = Field(default=True, alias="LIVE_TRADING_LOCKDOWN")
    live_lockdown_reason: str = Field(
        default="Live trading is locked until preflight passes.",
        alias="LIVE_LOCKDOWN_REASON",
    )
    exchange: str = Field(default="binance", alias="EXCHANGE")
    binance_account_type: str = Field(default="futures", alias="BINANCE_ACCOUNT_TYPE")

    # ============================================
    # Trading Symbols
    # ============================================
    symbols: str = Field(
        default="BTC/USDT,ETH/USDT,SOL/USDT", 
        alias="SYMBOLS"
    )

    # ============================================
    # Risk Management Parameters
    # ============================================
    max_risk_per_trade: float = Field(default=1.0, alias="MAX_RISK_PER_TRADE")
    daily_max_loss: float = Field(default=3.0, alias="DAILY_MAX_LOSS")
    max_leverage: float = Field(default=2.0, alias="MAX_LEVERAGE")
    confidence_threshold: int = Field(default=75, alias="CONFIDENCE_THRESHOLD")
    max_open_positions: int = Field(default=3, alias="MAX_OPEN_POSITIONS")
    live_order_confirmation: str = Field(default="", alias="LIVE_ORDER_CONFIRMATION")
    max_live_order_usdt: float = Field(default=15.0, alias="MAX_LIVE_ORDER_USDT")
    min_live_order_usdt: float = Field(default=5.0, alias="MIN_LIVE_ORDER_USDT")
    live_stop_loss_pct: float = Field(default=2.0, alias="LIVE_STOP_LOSS_PCT")
    live_take_profit_pct: float = Field(default=4.0, alias="LIVE_TAKE_PROFIT_PCT")

    # ============================================
    # Telegram Notifications
    # ============================================
    telegram_bot_token: Optional[str] = Field(None, alias="TELEGRAM_BOT_TOKEN", repr=False)
    telegram_chat_id: Optional[str] = Field(None, alias="TELEGRAM_CHAT_ID", repr=False)

    # ============================================
    # Logging
    # ============================================
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    refresh_interval: int = Field(default=30, alias="REFRESH_INTERVAL")

    # ============================================
    # Database
    # ============================================
    database_url: str = Field(
        default="sqlite:///./crypto_trader.db", 
        alias="DATABASE_URL"
    )

    # ============================================
    # Market Data
    # ============================================
    timeframes: str = Field(default="15m,1h,4h", alias="TIMEFRAMES")
    lookback_candles: int = Field(default=100, alias="LOOKBACK_CANDLES")
    max_symbols_per_cycle: int = Field(default=50, alias="MAX_SYMBOLS_PER_CYCLE")

    # ============================================
    # Rate Limiting
    # ============================================
    binance_rate_limit: int = Field(default=10, alias="BINANCE_RATE_LIMIT")
    coingecko_rate_limit: int = Field(default=5, alias="COINGECKO_RATE_LIMIT")

    # ============================================
    # Hedging
    # ============================================
    enable_hedging: bool = Field(default=True, alias="ENABLE_HEDGING")
    binance_position_mode: str = Field(default="one-way", alias="BINANCE_POSITION_MODE")

    # ============================================
    # Emergency
    # ============================================
    emergency_stop: bool = Field(default=False, alias="EMERGENCY_STOP")

    # ============================================
    # Validators
    # ============================================

    @validator(
        "groq_api_key",
        "binance_api_key",
        "binance_secret_key",
        "telegram_bot_token",
        "telegram_chat_id",
        "live_order_confirmation",
        pre=True,
    )
    def strip_env_strings(cls, v):
        """Trim accidental whitespace around secrets and control flags."""
        if isinstance(v, str):
            return v.strip()
        return v

    @validator("groq_api_key", pre=True, always=True)
    def validate_groq_key(cls, v):
        """Validate Groq API key is provided."""
        if not v:
            raise ValueError("GROQ_API_KEY is required")
        return v

    @validator("trading_mode")
    def validate_trading_mode(cls, v):
        """Validate trading mode is valid."""
        valid_modes = ["paper", "backtest", "live"]
        v = v.lower()
        if v not in valid_modes:
            raise ValueError(f"TRADING_MODE must be one of {valid_modes}")
        return v

    @validator("binance_account_type")
    def validate_binance_account_type(cls, v):
        """Validate live Binance account routing."""
        normalized = str(v).strip().lower().replace("-", "_")
        aliases = {
            "future": "futures",
            "usd_m": "futures",
            "usdm": "futures",
            "portfolio": "portfolio_margin",
            "papi": "portfolio_margin",
            "pm": "portfolio_margin",
        }
        normalized = aliases.get(normalized, normalized)
        valid_types = ["futures", "portfolio_margin"]
        if normalized not in valid_types:
            raise ValueError(f"BINANCE_ACCOUNT_TYPE must be one of {valid_types}")
        return normalized

    @validator("symbols")
    def validate_symbols(cls, v):
        """Allow only explicit USDT pair symbols used by the bot and exchange layer."""
        raw = str(v).strip().upper()
        dynamic_symbols = {"ALL", "ALL_USDT", "ALL_BINANCE", "ALL_BINANCE_USDT"}
        if raw in dynamic_symbols:
            return "ALL_USDT"

        symbols = [s.strip().upper() for s in raw.split(",") if s.strip()]
        if not symbols:
            raise ValueError("SYMBOLS must contain at least one symbol")
        if len(symbols) > 200:
            raise ValueError("SYMBOLS cannot contain more than 200 symbols")
        pattern = re.compile(r"^[A-Z0-9]{2,12}/USDT$")
        invalid = [symbol for symbol in symbols if not pattern.match(symbol)]
        if invalid:
            raise ValueError(f"Invalid SYMBOLS entries: {', '.join(invalid)}")
        return ",".join(symbols)

    @validator("max_risk_per_trade")
    def validate_max_risk(cls, v):
        """Validate risk per trade is reasonable."""
        if v <= 0 or v > 5:
            raise ValueError("MAX_RISK_PER_TRADE must be between 0 and 5")
        return v

    @validator("daily_max_loss")
    def validate_daily_max_loss(cls, v):
        """Validate daily max loss is reasonable."""
        if v <= 0 or v > 10:
            raise ValueError("DAILY_MAX_LOSS must be between 0 and 10")
        return v

    @validator("confidence_threshold")
    def validate_confidence(cls, v):
        """Validate confidence threshold is between 0 and 100."""
        if v < 0 or v > 100:
            raise ValueError("CONFIDENCE_THRESHOLD must be between 0 and 100")
        return v

    @validator("max_leverage")
    def validate_leverage(cls, v):
        """Validate leverage is reasonable."""
        if v < 1 or v > 20:
            raise ValueError("MAX_LEVERAGE must be between 1 and 20")
        return v

    @validator("max_symbols_per_cycle")
    def validate_max_symbols_per_cycle(cls, v):
        """Limit dynamic symbol scans so live loops remain operational."""
        if v < 1 or v > 200:
            raise ValueError("MAX_SYMBOLS_PER_CYCLE must be between 1 and 200")
        return v

    @validator("max_live_order_usdt")
    def validate_max_live_order(cls, v):
        """Validate the live order hard cap."""
        if v <= 0 or v > 1000:
            raise ValueError("MAX_LIVE_ORDER_USDT must be between 0 and 1000")
        return v

    @validator("min_live_order_usdt")
    def validate_min_live_order(cls, v):
        """Validate the live order minimum."""
        if v <= 0 or v > 1000:
            raise ValueError("MIN_LIVE_ORDER_USDT must be between 0 and 1000")
        return v

    @validator("live_stop_loss_pct")
    def validate_live_stop_loss(cls, v):
        """Validate live stop loss percentage."""
        if v <= 0 or v > 20:
            raise ValueError("LIVE_STOP_LOSS_PCT must be between 0 and 20")
        return v

    @validator("live_take_profit_pct")
    def validate_live_take_profit(cls, v):
        """Validate live take profit percentage."""
        if v < 0 or v > 50:
            raise ValueError("LIVE_TAKE_PROFIT_PCT must be between 0 and 50")
        return v

    # ============================================
    # Helper Methods
    # ============================================

    def get_symbols_list(self) -> list:
        """Parse symbols string into list."""
        return [s.strip() for s in self.symbols.split(",")]

    def uses_dynamic_symbols(self) -> bool:
        """Return True when Binance should discover active USDT symbols."""
        return self.symbols.upper() == "ALL_USDT"

    def get_timeframes_list(self) -> list:
        """Parse timeframes string into list."""
        return [t.strip() for t in self.timeframes.split(",")]

    def is_live_mode(self) -> bool:
        """Check if live trading is enabled."""
        return self.live_trading and self.trading_mode == "live"

    def is_paper_mode(self) -> bool:
        """Check if paper trading is enabled."""
        return self.trading_mode == "paper"

    def validate_live_mode(self) -> bool:
        """
        Validate all requirements for live trading.
        Returns True if safe to trade live, False otherwise.
        """
        if self.live_trading_lockdown:
            logger.error("Live trading lockdown is active: %s", self.live_lockdown_reason)
            return False

        if not self.live_trading:
            logger.warning("Live trading is disabled in .env")
            return False

        if self.trading_mode != "live":
            logger.warning(f"TRADING_MODE is '{self.trading_mode}', not 'live'")
            return False

        if not self.binance_api_key or not self.binance_secret_key:
            logger.error("BINANCE_API_KEY and BINANCE_SECRET_KEY are required for live trading")
            return False

        if self.live_order_confirmation != "I_ACCEPT_REAL_MONEY_RISK":
            logger.error(
                "LIVE_ORDER_CONFIRMATION must be set to I_ACCEPT_REAL_MONEY_RISK before live orders are allowed"
            )
            return False

        if self.min_live_order_usdt > self.max_live_order_usdt:
            logger.error("MIN_LIVE_ORDER_USDT cannot be greater than MAX_LIVE_ORDER_USDT")
            return False

        if self.emergency_stop:
            logger.error("Emergency stop is active - cannot trade")
            return False

        logger.info("Live trading requirements validated")
        return True


# ============================================
# Global Settings Instance
# ============================================

try:
    settings = Settings()
    logger.info(f"Configuration loaded successfully")
    logger.info(f"Trading Mode: {settings.trading_mode}")
    logger.info(f"Symbols: {settings.get_symbols_list()}")
except Exception as e:
    logger.critical(f"Failed to load configuration: {e}")
    raise
