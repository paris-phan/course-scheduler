import logging
import sys
from typing import Optional
from app.config import settings


def setup_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Set up and return a logger instance with consistent formatting.
    
    Args:
        name: Logger name (usually __name__ from the calling module)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name or "course_scheduler")
    
    # Only add handler if logger doesn't have one already
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(settings.LOG_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    return logger