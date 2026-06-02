"""Helper utilities."""
import logging
logger = logging.getLogger(__name__)

def safe_divide(num, denom, default=0):
    if denom == 0:
        return default
    return num / denom
