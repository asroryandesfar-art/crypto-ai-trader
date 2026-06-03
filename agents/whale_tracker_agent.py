"""Local whale activity estimates from cached public volume snapshots."""

from __future__ import annotations

import logging
from statistics import median

logger = logging.getLogger(__name__)


class WhaleTrackerAgent:
    """Detect public-volume anomalies without private exchange credentials."""

    name = "WhaleTracker"

    def __init__(self, exchange_service=None):
        self.exchange = exchange_service
        logger.info("WhaleTrackerAgent initialized")

    def analyze(self, symbol: str, market: dict, history: list[dict]) -> dict:
        current_volume = float(market.get("volume_24h") or 0)
        historic = [float(row.get("volume_24h") or 0) for row in history[-30:] if float(row.get("volume_24h") or 0) > 0]
        baseline = median(historic) if historic else current_volume
        ratio = current_volume / baseline if baseline else 1.0
        price_change = float(market.get("change_24h") or 0)
        pressure = "BUY" if price_change > 0.5 else "SELL" if price_change < -0.5 else "NEUTRAL"
        score = min(100, int(max(0, (ratio - 1) * 55) + min(abs(price_change), 8) * 4))
        anomalies = []
        if ratio >= 1.35:
            anomalies.append(f"24h public volume is {ratio:.2f}x cached median")
        if abs(price_change) >= 4:
            anomalies.append(f"price moved {price_change:+.2f}% with {pressure.lower()} pressure")
        confidence = min(95, 45 + len(historic) + (20 if anomalies else 0))
        result = {"symbol": symbol, "whale_activity_score": score, "anomalies": anomalies, "confidence": confidence, "pressure": pressure, "volume_ratio": round(ratio, 3), "source": "public_volume_cache"}
        logger.info("%s result=%s", self.name, result)
        return result
