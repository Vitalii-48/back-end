import logging
import sys
from app.core.config import settings

def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(settings.LOG_LEVEL)
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(settings.LOG_LEVEL)
        formatter = logging.Formatter(settings.LOG_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
