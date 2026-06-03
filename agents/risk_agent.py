"""Deterministic hard risk gate for all trading decisions."""

from __future__ import annotations

import logging
from risk.position_sizing import PositionSizer

logger = logging.getLogger(__name__)


class RiskAgent:
    """Apply non-AI safety policy. AI output cannot override this gate."""

    name = "RiskAgent"

    def __init__(self, config):
        self.config = config
        logger.info("RiskAgent initialized")

    def evaluate(self, action: str, confidence: int, liquidation: dict, emergency_stop: bool = False, daily_loss_hit: bool = False) -> dict:
        flags = []
        if self.config.trading_mode == "paper":
            flags.append("PAPER_MODE_ACTIVE")
        if not self.config.live_trading:
            flags.append("LIVE_TRADING_DISABLED")
        if self.config.live_trading_lockdown:
            flags.append("LIVE_LOCKDOWN_ACTIVE")
        if self.config.local_only_inference:
            flags.append("LOCAL_ONLY_INFERENCE")
        blocked = False
        if emergency_stop or self.config.emergency_stop:
            flags.append("EMERGENCY_STOP_ACTIVE")
            blocked = True
        if daily_loss_hit:
            flags.append("DAILY_LOSS_LIMIT_REACHED")
            blocked = True
        if int(confidence) < self.config.confidence_threshold:
            flags.append("BELOW_CONFIDENCE_THRESHOLD")
            blocked = True
        if liquidation.get("liquidation_risk") == "HIGH":
            flags.append("HIGH_LIQUIDATION_RISK")
            blocked = True
        approved_action = "HOLD" if blocked else action
        result = {"approved": not blocked, "requested_action": action, "approved_action": approved_action, "safety_flags": flags, "confidence_threshold": self.config.confidence_threshold, "max_risk_per_trade": self.config.max_risk_per_trade, "daily_max_loss": self.config.daily_max_loss}
        logger.info("%s result=%s", self.name, result)
        return result

    def calculate_live_notional(self, free_balance: float) -> float:
        sizer = PositionSizer(account_balance=free_balance, max_risk=self.config.max_risk_per_trade, max_notional=self.config.max_live_order_usdt)
        return sizer.calculate_notional(stop_loss_pct=self.config.live_stop_loss_pct, free_balance=free_balance, leverage=self.config.max_leverage)
