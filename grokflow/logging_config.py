"""
GrokFlow Logging Configuration

Provides comprehensive logging with:
- Rotating file handler (10MB max, 5 backups)
- Console handler for errors
- Structured logging with context
- Performance metrics logging
- No PII or sensitive data
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional


class SensitiveDataFilter(logging.Filter):
    """Filter to prevent sensitive data from being logged"""
    
    SENSITIVE_PATTERNS = [
        'api_key', 'apikey', 'api-key',
        'password', 'passwd', 'pwd',
        'token', 'secret', 'auth',
        'xai_api_key', 'XAI_API_KEY'
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter out log records containing sensitive data"""
        message = record.getMessage().lower()
        
        for pattern in self.SENSITIVE_PATTERNS:
            if pattern in message:
                # Redact the sensitive part
                record.msg = "[REDACTED - Sensitive data filtered]"
                record.args = ()
                break
        
        return True


def setup_logging(
    log_dir: Optional[Path] = None,
    level: str = "INFO",
    console_level: str = "ERROR"
) -> logging.Logger:
    """
    Setup comprehensive logging system for GrokFlow
    
    Args:
        log_dir: Directory for log files (default: ~/.grokflow/logs)
        level: File logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        console_level: Console logging level (default: ERROR)
        
    Returns:
        Configured logger instance
        
    Example:
        >>> logger = setup_logging()
        >>> logger.info("Application started")
        >>> logger.error("Error occurred", exc_info=True)
    """
    # Default log directory
    if log_dir is None:
        log_dir = Path.home() / ".grokflow" / "logs"
    
    # Create log directory
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger('grokflow')
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # File handler - rotating with date in filename
    log_file = log_dir / f"grokflow_{datetime.now():%Y%m%d}.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler - errors only
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(getattr(logging, console_level.upper()))
    
    # Detailed formatter for file logs
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - '
        '[%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Simple formatter for console
    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )
    
    file_handler.setFormatter(file_formatter)
    console_handler.setFormatter(console_formatter)
    
    # Add sensitive data filter
    sensitive_filter = SensitiveDataFilter()
    file_handler.addFilter(sensitive_filter)
    console_handler.addFilter(sensitive_filter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Log startup
    logger.info("=" * 80)
    logger.info("GrokFlow logging initialized")
    logger.info(f"Log file: {log_file}")
    logger.info(f"Log level: {level}")
    logger.info("=" * 80)
    
    return logger


def get_logger(name: str = 'grokflow') -> logging.Logger:
    """
    Get logger instance
    
    Args:
        name: Logger name (default: 'grokflow')
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Performance logging helpers
class PerformanceLogger:
    """Helper for logging performance metrics"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.timings = {}
    
    def start_timer(self, operation: str):
        """Start timing an operation"""
        self.timings[operation] = datetime.now()
        self.logger.debug(f"Started: {operation}")
    
    def end_timer(self, operation: str):
        """End timing and log duration"""
        if operation not in self.timings:
            self.logger.warning(f"Timer not started for: {operation}")
            return
        
        start_time = self.timings[operation]
        duration = (datetime.now() - start_time).total_seconds()
        
        self.logger.info(f"Completed: {operation} in {duration:.3f}s")
        
        # Warn on slow operations
        if duration > 5.0:
            self.logger.warning(f"Slow operation: {operation} took {duration:.3f}s")
        
        del self.timings[operation]
        return duration


# Context manager for operation logging
from contextlib import contextmanager

@contextmanager
def log_operation(logger: logging.Logger, operation: str):
    """
    Context manager for logging operations with timing
    
    Example:
        >>> with log_operation(logger, "analyze_image"):
        ...     # do work
        ...     pass
    """
    logger.info(f"Starting: {operation}")
    start_time = datetime.now()
    
    try:
        yield
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Completed: {operation} in {duration:.3f}s")
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        logger.error(
            f"Failed: {operation} after {duration:.3f}s - {e}",
            exc_info=True
        )
        raise
