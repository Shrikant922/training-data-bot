"""
Logging Setup - The Factory Communication System

This module provides structured logging for the Training Data Bot with context support,
rich formatting, and configurable log levels.
"""

import logging
import sys
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Dict, Optional

from rich.console import Console
from rich.logging import RichHandler

from .config import settings

# Context variables for request/operation tracking
log_context: ContextVar[Dict[str, Any]] = ContextVar("log_context", default={})


class LogContext:
    """
    Context manager for adding temporary context to log messages.

    Example:
        with LogContext(operation="load_pdf", document_id=doc.id):
            logger.info("Loading document")  # Will include operation and document_id
    """

    def __init__(self, **kwargs: Any):
        self.context = kwargs
        self.token = None

    def __enter__(self):
        current = log_context.get()
        new_context = {**current, **self.context}
        self.token = log_context.set(new_context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.token:
            log_context.reset(self.token)


class ContextualFormatter(logging.Formatter):
    """
    Custom formatter that includes context variables in log messages.
    """

    def format(self, record: logging.LogRecord) -> str:
        # Add context to the record
        context = log_context.get()
        if context:
            context_str = " | ".join(f"{k}={v}" for k, v in context.items())
            record.msg = f"[{context_str}] {record.msg}"

        return super().format(record)


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    use_rich: bool = True
) -> None:
    """
    Setup logging configuration for the entire application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output
        use_rich: Use rich formatting for console output
    """
    level = log_level or settings.log_level

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level.upper())

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler with Rich formatting
    if use_rich:
        console = Console(stderr=True)
        console_handler = RichHandler(
            console=console,
            rich_tracebacks=True,
            tracebacks_show_locals=settings.debug,
            show_time=True,
            show_path=settings.debug,
        )
    else:
        console_handler = logging.StreamHandler(sys.stderr)
        formatter = ContextualFormatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(formatter)

    console_handler.setLevel(level.upper())
    root_logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(level.upper())

        file_formatter = ContextualFormatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (usually module name or class name)

    Returns:
        Configured logger instance

    Example:
        logger = get_logger(__name__)
        logger.info("Starting process")

        # With context
        with LogContext(user_id=123):
            logger.info("User action")  # Automatically includes user_id
    """
    return logging.getLogger(f"training_data_bot.{name}")


# Initialize logging on import if not already configured
if not logging.getLogger().handlers:
    setup_logging()
