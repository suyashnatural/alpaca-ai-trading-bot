"""
src/logger.py
Centralised Loguru logger used across the entire bot.
"""

import sys
from loguru import logger
from config.settings import LOG_LEVEL

# Remove default handler then add ours
logger.remove()

# Console — coloured, human-readable
logger.add(
    sys.stdout,
    level=LOG_LEVEL,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
           "<level>{level: <8}</level> | "
           "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
           "<level>{message}</level>",
    colorize=True,
)

# File — rotating, 7 days retention
logger.add(
    "logs/bot_{time:YYYY-MM-DD}.log",
    level="DEBUG",
    rotation="00:00",        # new file every midnight
    retention="7 days",
    compression="zip",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
)

__all__ = ["logger"]
