"""Logging utilities."""
import logging
import sys
from typing import Optional
from config.settings import get_settings


def setup_logger(name: str = "bi_assessment", level: Optional[str] = None) -> logging.Logger:
    """Set up and return a logger instance."""
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
    
    settings = get_settings()
    log_level = level or settings.log_level
    
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    logger.propagate = False
    
    return logger


# Global logger instance
logger = setup_logger()

