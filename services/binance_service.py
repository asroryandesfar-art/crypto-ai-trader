"""Binance API service for market data."""
import logging
logger = logging.getLogger(__name__)
class BinanceService:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        logger.info("Binance service initialized")
