"""Notification service."""
import logging
logger = logging.getLogger(__name__)
class Notifier:
    def __init__(self, token=None, chat_id=None):
        self.token = token
        self.chat_id = chat_id
        logger.info("Notifier initialized")
