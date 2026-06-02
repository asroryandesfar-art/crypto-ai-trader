"""Position sizing calculator."""
import logging
logger = logging.getLogger(__name__)


class PositionSizer:
    def __init__(self, account_balance, max_risk=1.0, max_notional=None):
        self.account_balance = float(account_balance)
        self.max_risk = float(max_risk)
        self.max_notional = float(max_notional) if max_notional is not None else None
        logger.info("PositionSizer initialized")

    def calculate_notional(self, stop_loss_pct: float, free_balance: float | None = None, leverage: float = 1.0) -> float:
        """Risk-based notional where stop loss loss <= configured account risk."""
        if stop_loss_pct <= 0:
            raise ValueError("stop_loss_pct must be positive")
        balance = self.account_balance if free_balance is None else float(free_balance)
        if balance <= 0:
            return 0.0
        risk_budget = balance * (self.max_risk / 100)
        risk_notional = risk_budget / (float(stop_loss_pct) / 100)
        margin_cap = balance * max(1.0, float(leverage)) * 0.90
        candidates = [risk_notional, margin_cap]
        if self.max_notional is not None:
            candidates.append(self.max_notional)
        return max(0.0, min(candidates))

    def calculate_quantity(self, price: float, stop_loss_pct: float, free_balance: float | None = None, leverage: float = 1.0) -> float:
        """Calculate base quantity from risk notional and entry price."""
        if price <= 0:
            raise ValueError("price must be positive")
        return self.calculate_notional(stop_loss_pct, free_balance, leverage) / float(price)
