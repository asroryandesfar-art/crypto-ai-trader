"""CCXT exchange wrapper."""
import logging
logger = logging.getLogger(__name__)
class CCXTExchange:
    def __init__(self, exchange_name="binance"):
        self.exchange_name = exchange_name
        logger.info(f"CCXT {exchange_name} initialized")
