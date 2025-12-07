"""
Structured logging configuration using loguru and structlog.

Provides consistent, structured JSON logging across the application with
request IDs, job IDs, and contextual information for observability.
"""

import sys
import logging
from typing import Any, Dict
from pathlib import Path

from loguru import logger
import structlog
from structlog.typing import EventDict, WrappedLogger

from releaseradar.config import settings


class PII_Filter:
    """Filter to redact PII (emails, phone numbers, tokens) from logs."""
    
    PII_FIELDS = {
        "email", "phone", "password", "token", "api_key", "secret",
        "code", "verification", "auth", "bearer", "stripe", "key_hash"
    }
    
    def __call__(self, logger: WrappedLogger, name: str, event_dict: EventDict) -> EventDict:
        """Redact PII fields from event dictionary."""
        for key in list(event_dict.keys()):
            if any(pii_field in key.lower() for pii_field in self.PII_FIELDS):
                event_dict[key] = "[REDACTED]"
        return event_dict


def add_log_level(logger: WrappedLogger, name: str, event_dict: EventDict) -> EventDict:
    """Add log level to event dict."""
    event_dict["level"] = name.upper()
    return event_dict


def add_timestamp(logger: WrappedLogger, name: str, event_dict: EventDict) -> EventDict:
    """Add ISO timestamp to event dict."""
    from datetime import datetime
    event_dict["timestamp"] = datetime.utcnow().isoformat()
    return event_dict


class InterceptHandler(logging.Handler):
    """
    Intercept standard logging calls and route them through loguru.
    This ensures all logging (including from third-party libraries) uses our configuration.
    """
    
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def configure_logging() -> None:
    """Configure structured logging for the application."""
    
    # Remove default loguru handler
    logger.remove()
    
    # Determine log format
    if settings.log_format == "json":
        # JSON format for production
        log_format = "{message}"
        serialize = True
    else:
        # Human-readable format for development
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
        serialize = False
    
    # Add console handler
    logger.add(
        sys.stderr,
        format=log_format,
        level=settings.log_level,
        serialize=serialize,
        backtrace=True,
        diagnose=settings.is_development,
    )
    
    # Add file handler if log file is configured
    if settings.log_file:
        log_path = Path(settings.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            settings.log_file,
            format=log_format,
            level=settings.log_level,
            serialize=serialize,
            rotation="500 MB",
            retention="10 days",
            compression="zip",
            backtrace=True,
            diagnose=settings.is_development,
        )
    
    # Configure structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        add_timestamp,
        add_log_level,
        PII_Filter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    if settings.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Intercept standard logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # Silence noisy loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    logger.info(
        "Logging configured",
        level=settings.log_level,
        format=settings.log_format,
        environment=settings.app_env,
    )


def get_logger(name: str) -> Any:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


# Configure logging on module import
configure_logging()
