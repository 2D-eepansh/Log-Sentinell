"""
Logging configuration for production use.

Provides structured logging with file and console output.
Integrates with config for environment-specific log levels.
"""

import logging
import logging.handlers
from pathlib import Path

from .config import config


def setup_logging(logger_name: str = "anomaly_copilot") -> logging.Logger:
    """
    Configure and return a logger instance.
    
    Args:
        logger_name: Name of the logger (typically the module name)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(logger_name)
    
    # Don't add handlers if logger already configured
    if logger.handlers:
        return logger
    
    logger.setLevel(config.log_level)
    
    # Formatter for consistent output
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(config.log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (rotated daily)
    log_file = config.logs_dir / f"{logger_name}.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
    )
    file_handler.setLevel(config.log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


# Application root logger
logger = setup_logging()
