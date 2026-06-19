import sys
from loguru import logger

logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> | {message}",
    level="INFO",
)
logger.add(
    "logs/agent.log",
    rotation="10 MB",
    retention=7,
    level="DEBUG",
    encoding="utf-8",
)
