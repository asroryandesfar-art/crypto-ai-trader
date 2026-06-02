"""
Logging configuration module.
Sets up logging for the entire application.
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from utils.runtime_safety import install_secret_redaction

# Create logs directory if it doesn't exist
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)


def setup_logging(name: str, level: str = "INFO") -> logging.Logger:
    """
    Setup logger with file and console handlers.
    
    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level.upper())

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_formatter = logging.Formatter(
        fmt='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level.upper())
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler
    log_file = LOGS_DIR / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(level.upper())
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)

    install_secret_redaction(
        logger,
        (
            os.getenv("GROQ_API_KEY", ""),
            os.getenv("BINANCE_API_KEY", ""),
            os.getenv("BINANCE_SECRET_KEY", ""),
            os.getenv("TELEGRAM_BOT_TOKEN", ""),
        ),
    )

    return logger


# Create root logger
root_logger = setup_logging("crypto_trader", "INFO")
