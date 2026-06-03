"""Deterministic liquidation-risk estimate from local market pressure."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class LiquidationAgent:
    """Estimate liquidation pressure; does not place orders."""

    name = "LiquidationAgent"

    def __init__(self, exchange_service=None):
        self.exchange = exchange_service
        logger.info("LiquidationAgent initialized")

    def analyze(self, market: dict, technical: dict, whale: dict) -> dict:
        movement = float(market.get("change_24h") or 0)
        volatility = float(technical.get("volatility_pct") or 0)
        whale_score = float(whale.get("whale_activity_score") or 0)
        risk_score = min(100, int(abs(movement) * 7 + volatility * 14 + whale_score * 0.35))
        liquidation_risk = "HIGH" if risk_score >= 70 else "MEDIUM" if risk_score >= 38 else "LOW"
        direction = "LONG_LIQUIDATION_RISK" if movement < -1 else "SHORT_LIQUIDATION_RISK" if movement > 1 else "BALANCED"
        result = {"liquidation_risk": liquidation_risk, "risk_score": risk_score, "direction": direction, "rationale": f"24h move {movement:+.2f}%, local volatility {volatility:.2f}%, whale score {whale_score:.0f}."}
        logger.info("%s result=%s", self.name, result)
        return result
