"""News Agent - Analyzes crypto news."""
import logging
logger = logging.getLogger(__name__)
class NewsAgent:
    def __init__(self, groq_service):
        self.groq = groq_service
        logger.info("NewsAgent initialized")
