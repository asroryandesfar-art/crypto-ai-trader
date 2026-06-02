"""Daily loss guard."""
import logging
from datetime import date
logger = logging.getLogger(__name__)


class DailyLossGuard:
    def __init__(self, max_loss=3.0, balance=10000):
        self.max_loss = float(max_loss)
        self.balance = float(balance)
        self.current_date = date.today()
        self.realized_loss = 0.0
        logger.info("DailyLossGuard initialized")

    @property
    def loss_limit(self) -> float:
        return self.balance * (self.max_loss / 100)

    def record_pnl(self, pnl: float) -> None:
        if date.today() != self.current_date:
            self.current_date = date.today()
            self.realized_loss = 0.0
        if pnl < 0:
            self.realized_loss += abs(float(pnl))

    def can_trade(self) -> bool:
        return self.realized_loss < self.loss_limit

    def remaining_loss_budget(self) -> float:
        return max(0.0, self.loss_limit - self.realized_loss)
