"""Stop loss calculation."""
import logging
logger = logging.getLogger(__name__)
class StopLossCalculator:
    @staticmethod
    def calculate_fixed_percent(entry, percent, side="BUY"):
        if side == "BUY":
            return entry * (1 - percent/100)
        return entry * (1 + percent/100)
