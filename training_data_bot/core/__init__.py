"""Core package for configuration, logging, exceptions, and data models."""

from .config import settings
from .logging import get_logger, LogContext
from .exceptions import (
    TrainingDataBotError,
    ConfigurationError,
    DocumentLoadError,
    ProcessingError,
    ValidationError,
)
from .models import (
    # Base
    BaseEntity,
    # Enums
    DocumentType,
    TaskType,
    QualityMetric,
    ProcessingStatus,
    ExportFormat,
    # Document Family
    Document,
    TextChunk,
    # Task Family
    TaskTemplate,
    TaskResult,
    # Training Family
    TrainingExample,
    Dataset,
    # Quality Family
    QualityReport,
    # Operations Family
    ProcessingJob,
)

__all__ = [
    "settings",
    "get_logger",
    "LogContext",
    "TrainingDataBotError",
    "ConfigurationError",
    "DocumentLoadError",
    "ProcessingError",
    "ValidationError",
    "BaseEntity",
    "DocumentType",
    "TaskType",
    "QualityMetric",
    "ProcessingStatus",
    "ExportFormat",
    "Document",
    "TextChunk",
    "TaskTemplate",
    "TaskResult",
    "TrainingExample",
    "Dataset",
    "QualityReport",
    "ProcessingJob",
]
