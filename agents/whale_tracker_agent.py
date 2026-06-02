"""Whale Tracker Agent - Monitors whale activity."""
import logging
logger = logging.getLogger(__name__)
class WhaleTrackerAgent:
    def __init__(self, exchange_service):
        self.exchange = exchange_service
        logger.info("WhaleTrackerAgent initialized")
