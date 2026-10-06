"""
Custom Exceptions - The Factory Alert System

This module defines all custom exceptions used throughout the Training Data Bot.
Organized by component for clear error handling.
"""

from typing import Any, Dict, Optional


# =============================================================================
# BASE EXCEPTIONS
# =============================================================================

class TrainingDataBotError(Exception):
    """
    Base exception for all Training Data Bot errors.

    All custom exceptions inherit from this, making it easy to catch
    any bot-related error.
    """

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        self.message = message
        self.details = details or {}
        self.original_error = original_error
        super().__init__(self.message)

    def __str__(self) -> str:
        base_msg = self.message
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            base_msg = f"{base_msg} ({details_str})"
        if self.original_error:
            base_msg = f"{base_msg} [Caused by: {self.original_error}]"
        return base_msg


# =============================================================================
# CONFIGURATION EXCEPTIONS
# =============================================================================

class ConfigurationError(TrainingDataBotError):
    """
    Raised when there's an issue with configuration settings.

    Example:
        - Missing required API key
        - Invalid configuration value
        - Conflicting settings
    """
    pass


class ValidationError(TrainingDataBotError):
    """
    Raised when data validation fails.

    Example:
        - Invalid document format
        - Pydantic validation error
        - Schema mismatch
    """
    pass


# =============================================================================
# DOCUMENT LOADING EXCEPTIONS
# =============================================================================

class DocumentLoadError(TrainingDataBotError):
    """
    Base exception for document loading errors.
    """
    pass


class FileNotFoundError(DocumentLoadError):
    """
    Raised when a source file cannot be found.
    """
    pass


class UnsupportedFormatError(DocumentLoadError):
    """
    Raised when trying to load an unsupported file format.

    Example:
        - Trying to load a .exe file
        - Format not in enabled_formats
    """
    pass


class FileSizeError(DocumentLoadError):
    """
    Raised when a file exceeds size limits.
    """
    pass


class DocumentParseError(DocumentLoadError):
    """
    Raised when document parsing fails.

    Example:
        - Corrupted PDF
        - Invalid JSON structure
        - Malformed HTML
    """
    pass


# =============================================================================
# WEB LOADING EXCEPTIONS
# =============================================================================

class WebLoadError(TrainingDataBotError):
    """
    Base exception for web loading errors.
    """
    pass


class URLError(WebLoadError):
    """
    Raised when URL is invalid or malformed.
    """
    pass


class HTTPError(WebLoadError):
    """
    Raised when HTTP request fails.

    Example:
        - 404 Not Found
        - 500 Server Error
        - Connection timeout
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        url: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        details["status_code"] = status_code
        details["url"] = url
        kwargs["details"] = details
        super().__init__(message, **kwargs)
        self.status_code = status_code
        self.url = url


# =============================================================================
# PROCESSING EXCEPTIONS
# =============================================================================

class ProcessingError(TrainingDataBotError):
    """
    Base exception for processing errors.
    """
    pass


class ChunkingError(ProcessingError):
    """
    Raised when text chunking fails.
    """
    pass


class TaskGenerationError(ProcessingError):
    """
    Raised when task generation fails.

    Example:
        - AI API error
        - Invalid task template
        - Output parsing error
    """
    pass


class PreprocessingError(ProcessingError):
    """
    Raised when text preprocessing fails.
    """
    pass


# =============================================================================
# AI CLIENT EXCEPTIONS
# =============================================================================

class AIClientError(TrainingDataBotError):
    """
    Base exception for AI client errors.
    """
    pass


class APIKeyError(AIClientError):
    """
    Raised when API key is missing or invalid.
    """
    pass


class APIRequestError(AIClientError):
    """
    Raised when API request fails.

    Example:
        - Rate limit exceeded
        - Invalid request format
        - Model not found
    """

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        details["provider"] = provider
        details["model"] = model
        kwargs["details"] = details
        super().__init__(message, **kwargs)
        self.provider = provider
        self.model = model


class RateLimitError(AIClientError):
    """
    Raised when API rate limit is exceeded.
    """
    pass


class TokenLimitError(AIClientError):
    """
    Raised when token limit is exceeded.
    """
    pass


# =============================================================================
# QUALITY EVALUATION EXCEPTIONS
# =============================================================================

class EvaluationError(TrainingDataBotError):
    """
    Base exception for quality evaluation errors.
    """
    pass


class QualityCheckError(EvaluationError):
    """
    Raised when quality check fails.
    """
    pass


class ThresholdError(EvaluationError):
    """
    Raised when data doesn't meet quality thresholds.
    """
    pass


# =============================================================================
# STORAGE/EXPORT EXCEPTIONS
# =============================================================================

class StorageError(TrainingDataBotError):
    """
    Base exception for storage/export errors.
    """
    pass


class ExportError(StorageError):
    """
    Raised when dataset export fails.
    """
    pass


class DatabaseError(StorageError):
    """
    Raised when database operation fails.
    """
    pass


class InvalidFormatError(StorageError):
    """
    Raised when export format is invalid or unsupported.
    """
    pass


# =============================================================================
# DECODO CLIENT EXCEPTIONS
# =============================================================================

class DecodoError(TrainingDataBotError):
    """
    Base exception for Decodo client errors.
    """
    pass


class DecodoAPIError(DecodoError):
    """
    Raised when Decodo API request fails.
    """
    pass


class DecodoAuthError(DecodoError):
    """
    Raised when Decodo authentication fails.
    """
    pass
