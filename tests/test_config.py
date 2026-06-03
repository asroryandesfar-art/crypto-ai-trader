"""Tests for Settings validation."""

import pytest
from config import Settings


def _make(**kwargs):
    """Build a Settings object with defaults overridden by kwargs."""
    defaults = {
        "AI_PROVIDER": "qvac",
        "TRADING_MODE": "paper",
        "SYMBOLS": "BTC/USDT,ETH/USDT",
        "LIVE_TRADING": "false",
        "LIVE_TRADING_LOCKDOWN": "true",
    }
    defaults.update(kwargs)
    return Settings(**defaults)


# ── ai_provider ──────────────────────────────────────────────────────────────

def test_ai_provider_qvac():
    s = _make(AI_PROVIDER="qvac")
    assert s.ai_provider == "qvac"


def test_ai_provider_local_qvac_alias():
    s = _make(AI_PROVIDER="local_qvac")
    assert s.ai_provider == "qvac"


def test_ai_provider_groq():
    s = _make(AI_PROVIDER="groq")
    assert s.ai_provider == "groq"


def test_ai_provider_invalid():
    with pytest.raises(Exception):
        _make(AI_PROVIDER="openai")


# ── trading_mode ──────────────────────────────────────────────────────────────

def test_trading_mode_paper():
    s = _make(TRADING_MODE="paper")
    assert s.trading_mode == "paper"
    assert s.is_paper_mode() is True


def test_trading_mode_live():
    s = _make(TRADING_MODE="live")
    assert s.trading_mode == "live"


def test_trading_mode_invalid():
    with pytest.raises(Exception):
        _make(TRADING_MODE="sim")


# ── symbols ───────────────────────────────────────────────────────────────────

def test_symbols_normalised_to_uppercase():
    s = _make(SYMBOLS="btc/usdt,eth/usdt")
    assert "BTC/USDT" in s.get_symbols_list()


def test_symbols_single():
    s = _make(SYMBOLS="SOL/USDT")
    assert s.get_symbols_list() == ["SOL/USDT"]


def test_symbols_all_usdt():
    s = _make(SYMBOLS="ALL_USDT")
    assert s.uses_dynamic_symbols() is True


def test_symbols_dynamic_aliases():
    for alias in ("ALL", "ALL_BINANCE"):
        s = _make(SYMBOLS=alias)
        assert s.uses_dynamic_symbols() is True


def test_symbols_invalid_format():
    with pytest.raises(Exception):
        _make(SYMBOLS="BTCUSDT")


def test_symbols_invalid_dash():
    with pytest.raises(Exception):
        _make(SYMBOLS="BTC-USDT")


def test_symbols_empty():
    with pytest.raises(Exception):
        _make(SYMBOLS="")


def test_symbols_too_many():
    many = ",".join(f"{chr(65+i%26)}{chr(65+(i//26)%26)}/USDT" for i in range(201))
    with pytest.raises(Exception):
        _make(SYMBOLS=many)


# ── risk parameters ───────────────────────────────────────────────────────────

def test_max_risk_per_trade_valid():
    s = _make(MAX_RISK_PER_TRADE="2")
    assert s.max_risk_per_trade == pytest.approx(2.0)


def test_max_risk_per_trade_zero_raises():
    with pytest.raises(Exception):
        _make(MAX_RISK_PER_TRADE="0")


def test_max_risk_per_trade_too_high_raises():
    with pytest.raises(Exception):
        _make(MAX_RISK_PER_TRADE="6")


def test_confidence_threshold_valid():
    s = _make(CONFIDENCE_THRESHOLD="80")
    assert s.confidence_threshold == 80


def test_confidence_threshold_out_of_range():
    with pytest.raises(Exception):
        _make(CONFIDENCE_THRESHOLD="101")


def test_max_leverage_valid():
    s = _make(MAX_LEVERAGE="5")
    assert s.max_leverage == pytest.approx(5.0)


def test_max_leverage_too_high():
    with pytest.raises(Exception):
        _make(MAX_LEVERAGE="21")


def test_daily_max_loss_valid():
    s = _make(DAILY_MAX_LOSS="5")
    assert s.daily_max_loss == pytest.approx(5.0)


def test_daily_max_loss_out_of_range():
    with pytest.raises(Exception):
        _make(DAILY_MAX_LOSS="11")


# ── live order limits ─────────────────────────────────────────────────────────

def test_max_live_order_usdt_valid():
    s = _make(MAX_LIVE_ORDER_USDT="50")
    assert s.max_live_order_usdt == pytest.approx(50.0)


def test_min_live_order_usdt_valid():
    s = _make(MIN_LIVE_ORDER_USDT="5")
    assert s.min_live_order_usdt == pytest.approx(5.0)


# ── helper methods ────────────────────────────────────────────────────────────

def test_get_timeframes_list():
    s = _make(TIMEFRAMES="15m,1h,4h")
    assert s.get_timeframes_list() == ["15m", "1h", "4h"]


def test_is_live_mode_false_in_paper():
    s = _make(TRADING_MODE="paper", LIVE_TRADING="false")
    assert s.is_live_mode() is False


def test_is_live_mode_false_when_trading_mode_not_live():
    s = _make(TRADING_MODE="paper", LIVE_TRADING="true")
    assert s.is_live_mode() is False


def test_paper_account_balance_default():
    s = _make()
    assert s.paper_account_balance == pytest.approx(10000.0)


def test_paper_account_balance_custom():
    s = _make(PAPER_ACCOUNT_BALANCE="5000")
    assert s.paper_account_balance == pytest.approx(5000.0)


# ── binance account type ──────────────────────────────────────────────────────

def test_binance_account_type_futures():
    s = _make(BINANCE_ACCOUNT_TYPE="futures")
    assert s.binance_account_type == "futures"


def test_binance_account_type_aliases():
    for alias in ("future", "usd_m", "usdm"):
        s = _make(BINANCE_ACCOUNT_TYPE=alias)
        assert s.binance_account_type == "futures"


def test_binance_account_type_portfolio_margin():
    s = _make(BINANCE_ACCOUNT_TYPE="portfolio_margin")
    assert s.binance_account_type == "portfolio_margin"


def test_binance_account_type_papi_alias():
    s = _make(BINANCE_ACCOUNT_TYPE="papi")
    assert s.binance_account_type == "portfolio_margin"


def test_binance_account_type_invalid():
    with pytest.raises(Exception):
        _make(BINANCE_ACCOUNT_TYPE="spot")
