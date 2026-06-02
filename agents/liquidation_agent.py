"""Liquidation Agent - Detects liquidation clusters."""
import logging
logger = logging.getLogger(__name__)
class LiquidationAgent:
    def __init__(self, exchange_service):
        self.exchange = exchange_service
        logger.info("LiquidationAgent initialized")
