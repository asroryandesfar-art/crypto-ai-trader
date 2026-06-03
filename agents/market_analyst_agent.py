"""Local market analyst using cached and public market snapshots."""

from __future__ import annotations

import logging
from statistics import mean, pstdev

logger = logging.getLogger(__name__)


def _ema(values: list[float], period: int) -> float:
    if not values:
        return 0.0
    weight = 2 / (period + 1)
    result = values[0]
    for value in values[1:]:
        result = (value * weight) + (result * (1 - weight))
    return result


def _rsi(values: list[float], period: int = 14) -> float:
    changes = [current - previous for previous, current in zip(values, values[1:])]
    if not changes:
        return 50.0
    window = changes[-period:]
    gains = sum(max(change, 0) for change in window) / len(window)
    losses = sum(abs(min(change, 0)) for change in window) / len(window)
    if losses == 0:
        return 100.0 if gains else 50.0
    return 100 - (100 / (1 + (gains / losses)))


class MarketAnalystAgent:
    """Compute deterministic edge indicators from local snapshot history."""

    name = "MarketAnalyst"

    def __init__(self, exchange_service=None):
        self.exchange = exchange_service
        logger.info("MarketAnalystAgent initialized")

    def analyze(self, symbol: str, market: dict, history: list[dict]) -> dict:
        prices = [float(item.get("price") or 0) for item in history if float(item.get("price") or 0) > 0]
        current = float(market.get("price") or 0)
        if current > 0 and (not prices or prices[-1] != current):
            prices.append(current)
        prices = prices[-100:]
        returns = [((b - a) / a) * 100 for a, b in zip(prices, prices[1:]) if a]
        sma_period = min(20, len(prices))
        sma = mean(prices[-sma_period:]) if prices else current
        ema = _ema(prices[-min(20, len(prices)):], min(12, max(2, len(prices)))) if prices else current
        momentum = ((prices[-1] - prices[-min(12, len(prices))]) / prices[-min(12, len(prices))] * 100) if len(prices) > 1 and prices[-min(12, len(prices))] else float(market.get("change_24h") or 0)
        volatility = pstdev(returns[-20:]) if len(returns) > 1 else abs(float(market.get("change_24h") or 0)) / 4
        rsi = _rsi(prices)
        score = 0
        score += 1 if current >= ema else -1
        score += 1 if current >= sma else -1
        score += 1 if momentum >= 0.4 else -1 if momentum <= -0.4 else 0
        score += -1 if rsi >= 72 else 1 if rsi <= 32 else 0
        vote = "BUY" if score >= 2 else "SELL" if score <= -2 else "HOLD"
        confidence = min(95, int(52 + abs(score) * 9 + min(abs(momentum), 4) * 3))
        result = {
            "symbol": symbol, "rsi": round(rsi, 2), "sma": round(sma, 8),
            "ema": round(ema, 8), "momentum_pct": round(momentum, 3),
            "volatility_pct": round(volatility, 3), "sample_count": len(prices),
            "vote": vote, "confidence": confidence,
            "rationale": f"RSI {rsi:.1f}, momentum {momentum:+.2f}%, volatility {volatility:.2f}%.",
        }
        logger.info("%s result=%s", self.name, result)
        return result
