"""Logging configuration for NOAA Listener."""

import logging
import sys
import uuid
import threading
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional

import noaa_listener.config as config_module

# Thread-local storage for correlation IDs
_thread_local = threading.local()


def get_correlation_id() -> str:
    """Get or create correlation ID for current context.
    
    Returns:
        Correlation ID string
    """
    if not hasattr(_thread_local, 'correlation_id'):
        _thread_local.correlation_id = str(uuid.uuid4())[:8]
    return _thread_local.correlation_id


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID for current context.
    
    Args:
        correlation_id: Correlation ID to set
    """
    _thread_local.correlation_id = correlation_id


class CorrelationIdFilter(logging.Filter):
    """Add correlation ID to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation_id to the log record.
        
        Args:
            record: Log record to filter
            
        Returns:
            Always True (don't filter out any records)
        """
        record.correlation_id = get_correlation_id()
        return True


def setup_logger(name: str, config: Optional[object] = None) -> logging.Logger:
    """Set up a logger with file and console handlers.
    
    Args:
        name: Logger name
        config: Configuration object (if None, will load default)
        
    Returns:
        Configured logger instance
    """
    if config is None:
        config = config_module.get_config()
    
    logger = logging.getLogger(name)
    logger.setLevel(config.log_level)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    # Create formatters
    formatter = logging.Formatter(
        config.log_format,
        datefmt=config.log_date_format
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(config.log_level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(CorrelationIdFilter())
    logger.addHandler(console_handler)
    
    # File handler
    try:
        log_file = Path(config.log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=config.log_max_file_size,
            backupCount=config.log_backup_count
        )
        file_handler.setLevel(config.log_level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(CorrelationIdFilter())
        logger.addHandler(file_handler)
    except (PermissionError, OSError) as e:
        # Log file not writable (e.g. read-only or unowned volume mount) — stdout only
        logging.getLogger(__name__).warning(
            "Could not create log file handler for '%s': %s. Logging to stdout only.",
            config.log_file, e
        )
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return setup_logger(name)
