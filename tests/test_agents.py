"""Tests for deterministic agent logic (no network calls)."""

import pytest
from agents.market_analyst_agent import MarketAnalystAgent, _ema, _rsi
from agents.sentiment_agent import SentimentAgent
from agents.whale_tracker_agent import WhaleTrackerAgent
from agents.liquidation_agent import LiquidationAgent
from agents.news_agent import NewsAgent


# ── helpers ──────────────────────────────────────────────────────────────────

def _history(count=20, base=50000.0, step=100.0):
    return [
        {"price": base + i * step, "change_24h": 0.1 * i, "market_cap": 1e12, "volume_24h": 4e9}
        for i in range(count)
    ]


MARKET_UP = {"price": 52000.0, "change_24h": 4.0, "market_cap": 1e12, "volume_24h": 5e9, "source": "test"}
MARKET_DOWN = {"price": 48000.0, "change_24h": -4.5, "market_cap": 1e12, "volume_24h": 6e9, "source": "test"}
MARKET_FLAT = {"price": 50000.0, "change_24h": 0.1, "market_cap": 1e12, "volume_24h": 4e9, "source": "test"}


# ── _ema ─────────────────────────────────────────────────────────────────────

def test_ema_empty():
    assert _ema([], 12) == 0.0


def test_ema_single():
    assert _ema([100.0], 12) == 100.0


def test_ema_tracks_uptrend():
    prices = [float(i) for i in range(1, 21)]
    result = _ema(prices, 12)
    assert result > prices[0], "EMA of uptrend should be above starting price"
    assert result <= prices[-1]


# ── _rsi ─────────────────────────────────────────────────────────────────────

def test_rsi_single_price():
    assert _rsi([50.0]) == 50.0


def test_rsi_all_gains_returns_100():
    assert _rsi([float(i) for i in range(1, 20)]) == 100.0


def test_rsi_all_losses_returns_0():
    assert _rsi([float(i) for i in range(20, 0, -1)]) == 0.0


def test_rsi_flat_returns_50():
    assert _rsi([100.0] * 15) == 50.0


def test_rsi_in_range():
    import random
    random.seed(42)
    prices = [100 + random.gauss(0, 2) for _ in range(30)]
    result = _rsi(prices)
    assert 0.0 <= result <= 100.0


# ── MarketAnalystAgent ────────────────────────────────────────────────────────

class TestMarketAnalystAgent:
    def setup_method(self):
        self.agent = MarketAnalystAgent()

    def test_result_has_required_keys(self):
        result = self.agent.analyze("BTC/USDT", MARKET_UP, _history())
        for key in ("symbol", "rsi", "sma", "ema", "momentum_pct", "volatility_pct", "vote", "confidence", "rationale"):
            assert key in result

    def test_vote_is_valid(self):
        for market in (MARKET_UP, MARKET_DOWN, MARKET_FLAT):
            result = self.agent.analyze("BTC/USDT", market, _history())
            assert result["vote"] in ("BUY", "SELL", "HOLD")

    def test_confidence_in_range(self):
        result = self.agent.analyze("BTC/USDT", MARKET_UP, _history())
        assert 0 <= result["confidence"] <= 100

    def test_empty_history_uses_current_price(self):
        result = self.agent.analyze("ETH/USDT", MARKET_FLAT, [])
        assert result["symbol"] == "ETH/USDT"
        assert result["vote"] in ("BUY", "SELL", "HOLD")

    def test_sample_count_reflects_history(self):
        result = self.agent.analyze("BTC/USDT", MARKET_UP, _history(20))
        assert result["sample_count"] <= 101  # history + current

    def test_uptrend_history_tends_buy(self):
        long_up = _history(50, base=40000.0, step=300.0)
        result = self.agent.analyze("BTC/USDT", {"price": 55000.0, "change_24h": 5.0, "market_cap": 1e12, "volume_24h": 5e9}, long_up)
        assert result["vote"] in ("BUY", "HOLD")

    def test_symbol_propagated(self):
        result = self.agent.analyze("SOL/USDT", MARKET_UP, _history())
        assert result["symbol"] == "SOL/USDT"


# ── SentimentAgent ────────────────────────────────────────────────────────────

class TestSentimentAgent:
    def setup_method(self):
        self.agent = SentimentAgent()

    def _news(self, sentiment="NEUTRAL", impact=0):
        return {"sentiment": sentiment, "impact_score": impact, "headline_count": 5}

    def test_bullish_fg_plus_bullish_news_gives_positive_score(self):
        fg = {"value": 75, "classification": "Greed", "source": "test"}
        result = self.agent.analyze(self._news("BULLISH", 50), fg)
        assert result["sentiment_score"] > 0
        assert result["label"] == "BULLISH"

    def test_fearful_fg_plus_bearish_news_gives_negative_score(self):
        fg = {"value": 20, "classification": "Extreme Fear", "source": "test"}
        result = self.agent.analyze(self._news("BEARISH", 50), fg)
        assert result["sentiment_score"] < 0
        assert result["label"] == "BEARISH"

    def test_neutral_fg_neutral_news_gives_neutral(self):
        fg = {"value": 50, "classification": "Neutral", "source": "test"}
        result = self.agent.analyze(self._news(), fg)
        assert result["label"] == "NEUTRAL"

    def test_fallback_fg_when_none(self):
        result = self.agent.analyze(self._news(), None)
        assert "sentiment_score" in result
        assert result["fear_greed"] == 50

    def test_score_clamped_to_100(self):
        fg = {"value": 100, "classification": "Extreme Greed", "source": "test"}
        result = self.agent.analyze(self._news("BULLISH", 100), fg)
        assert -100 <= result["sentiment_score"] <= 100

    def test_provider_is_local_rules_without_ai_service(self):
        result = self.agent.analyze(self._news(), None, use_qvac_summary=False)
        assert result["provider"] == "local_rules"


# ── WhaleTrackerAgent ─────────────────────────────────────────────────────────

class TestWhaleTrackerAgent:
    def setup_method(self):
        self.agent = WhaleTrackerAgent()

    def test_result_has_required_keys(self):
        result = self.agent.analyze("BTC/USDT", MARKET_UP, _history())
        for key in ("symbol", "whale_activity_score", "pressure", "volume_ratio", "confidence"):
            assert key in result

    def test_score_in_range(self):
        result = self.agent.analyze("BTC/USDT", MARKET_UP, _history())
        assert 0 <= result["whale_activity_score"] <= 100

    def test_confidence_in_range(self):
        result = self.agent.analyze("BTC/USDT", MARKET_UP, _history())
        assert 0 <= result["confidence"] <= 100

    def test_pressure_valid_values(self):
        for market in (MARKET_UP, MARKET_DOWN, MARKET_FLAT):
            result = self.agent.analyze("BTC/USDT", market, _history())
            assert result["pressure"] in ("BUY", "SELL", "NEUTRAL")

    def test_high_volume_triggers_anomaly(self):
        high_vol_market = {**MARKET_UP, "volume_24h": 20e9}
        result = self.agent.analyze("BTC/USDT", high_vol_market, _history())
        assert result["volume_ratio"] > 1.0

    def test_empty_history_does_not_crash(self):
        result = self.agent.analyze("ETH/USDT", MARKET_FLAT, [])
        assert result["symbol"] == "ETH/USDT"

    def test_symbol_propagated(self):
        result = self.agent.analyze("SOL/USDT", MARKET_FLAT, _history())
        assert result["symbol"] == "SOL/USDT"


# ── LiquidationAgent ─────────────────────────────────────────────────────────

class TestLiquidationAgent:
    def setup_method(self):
        self.agent = LiquidationAgent()

    def _whale(self, score=10, pressure="NEUTRAL"):
        return {"whale_activity_score": score, "pressure": pressure}

    def _technical(self, volatility=0.5):
        return {"volatility_pct": volatility}

    def test_result_has_required_keys(self):
        result = self.agent.analyze(MARKET_UP, self._technical(), self._whale())
        for key in ("liquidation_risk", "risk_score", "direction", "rationale"):
            assert key in result

    def test_risk_level_valid(self):
        for market in (MARKET_UP, MARKET_DOWN, MARKET_FLAT):
            result = self.agent.analyze(market, self._technical(), self._whale())
            assert result["liquidation_risk"] in ("LOW", "MEDIUM", "HIGH")

    def test_high_volatility_raises_risk(self):
        low_vol = self.agent.analyze(MARKET_FLAT, self._technical(0.1), self._whale(0))
        high_vol = self.agent.analyze(MARKET_FLAT, self._technical(5.0), self._whale(50))
        assert high_vol["risk_score"] >= low_vol["risk_score"]

    def test_big_move_down_gives_long_liquidation_risk(self):
        big_drop = {**MARKET_DOWN, "change_24h": -8.0}
        result = self.agent.analyze(big_drop, self._technical(2.0), self._whale(30))
        assert result["direction"] == "LONG_LIQUIDATION_RISK"

    def test_big_move_up_gives_short_liquidation_risk(self):
        big_pump = {**MARKET_UP, "change_24h": 8.0}
        result = self.agent.analyze(big_pump, self._technical(2.0), self._whale(30))
        assert result["direction"] == "SHORT_LIQUIDATION_RISK"

    def test_risk_score_in_range(self):
        result = self.agent.analyze(MARKET_DOWN, self._technical(3.0), self._whale(80))
        assert 0 <= result["risk_score"] <= 100


# ── NewsAgent (local rule path only) ─────────────────────────────────────────

class TestNewsAgent:
    def setup_method(self):
        self.agent = NewsAgent(ai_service=None)

    def _headlines(self, titles):
        return [{"title": t, "published": "", "link": ""} for t in titles]

    def test_bullish_keywords_produce_bullish_sentiment(self):
        headlines = self._headlines(["Bitcoin rally gains momentum", "Adoption surge record high"])
        result = self.agent.analyze(headlines, use_qvac_summary=False)
        assert result["sentiment"] == "BULLISH"

    def test_bearish_keywords_produce_bearish_sentiment(self):
        headlines = self._headlines(["Bitcoin crash hack fraud", "Bear market selloff risk decline"])
        result = self.agent.analyze(headlines, use_qvac_summary=False)
        assert result["sentiment"] == "BEARISH"

    def test_empty_headlines_produces_neutral(self):
        result = self.agent.analyze([], use_qvac_summary=False)
        assert result["sentiment"] == "NEUTRAL"
        assert result["impact_score"] == 0

    def test_result_has_required_keys(self):
        result = self.agent.analyze([], use_qvac_summary=False)
        for key in ("impact_score", "sentiment", "key_events", "summary", "provider", "headline_count"):
            assert key in result

    def test_impact_score_in_range(self):
        headlines = self._headlines(["Huge rally", "Big surge", "Growth record", "Launch bull"])
        result = self.agent.analyze(headlines, use_qvac_summary=False)
        assert 0 <= result["impact_score"] <= 100

    def test_provider_local_rules_without_ai_service(self):
        result = self.agent.analyze([], use_qvac_summary=False)
        assert result["provider"] == "local_rules"

    def test_cache_returns_same_result(self):
        headlines = self._headlines(["Surge rally gains"])
        r1 = self.agent.analyze(headlines, use_qvac_summary=False)
        r2 = self.agent.analyze(use_qvac_summary=False)
        assert r2["sentiment"] == r1["sentiment"]
