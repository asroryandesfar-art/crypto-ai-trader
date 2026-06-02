"""Sentiment Agent - Analyzes market sentiment."""
import logging
logger = logging.getLogger(__name__)
class SentimentAgent:
    def __init__(self, fear_greed_service, news_agent):
        self.fear_greed = fear_greed_service
        self.news_agent = news_agent
        logger.info("SentimentAgent initialized")
