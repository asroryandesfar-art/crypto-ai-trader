"""Risk Agent - Calculates and manages risk."""
import logging
from risk.position_sizing import PositionSizer

logger = logging.getLogger(__name__)


class RiskAgent:
    def __init__(self, config):
        self.config = config
        logger.info("RiskAgent initialized")

    def calculate_live_notional(self, free_balance: float) -> float:
        sizer = PositionSizer(
            account_balance=free_balance,
            max_risk=self.config.max_risk_per_trade,
            max_notional=self.config.max_live_order_usdt,
        )
        return sizer.calculate_notional(
            stop_loss_pct=self.config.live_stop_loss_pct,
            free_balance=free_balance,
            leverage=self.config.max_leverage,
        )
