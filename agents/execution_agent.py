"""Execution Agent - Executes trades on exchange."""
import logging
logger = logging.getLogger(__name__)
class ExecutionAgent:
    def __init__(self, exchange_service, mode="paper"):
        self.exchange = exchange_service
        self.mode = mode
        logger.info(f"ExecutionAgent initialized - Mode: {mode}")
