"""
Configuration Management - The Factory Rule Book

This module handles all configuration settings for the Training Data Bot using
Pydantic's BaseSettings for automatic environment variable loading and validation.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Main configuration class for the Training Data Bot.

    All settings can be overridden via environment variables.
    Example: export TRAINING_DATA_BOT_LOG_LEVEL=DEBUG
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_prefix="TRAINING_DATA_BOT_",
    )

    # -------------------------------------------------------------------------
    # Application Settings
    # -------------------------------------------------------------------------
    app_name: str = "Training Data Bot"
    version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"

    # -------------------------------------------------------------------------
    # AI / LLM Settings
    # -------------------------------------------------------------------------
    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.7
    openai_max_tokens: int = 4096

    # Anthropic
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-5-haiku-20241022"
    anthropic_temperature: float = 0.7
    anthropic_max_tokens: int = 4096

    # Default AI Provider
    default_ai_provider: str = "openai"  # "openai" or "anthropic"

    # -------------------------------------------------------------------------
    # Document Processing Settings
    # -------------------------------------------------------------------------
    # Chunking
    chunk_size: int = 1000
    chunk_overlap: int = 200
    min_chunk_size: int = 100

    # Parallel processing
    max_workers: int = 4
    max_concurrent_requests: int = 15

    # Caching
    enable_cache: bool = True

    # File size limits (in bytes)
    max_file_size: int = 50 * 1024 * 1024  # 50 MB
    max_total_size: int = 500 * 1024 * 1024  # 500 MB

    # Supported formats (subset of DocumentType)
    enabled_formats: List[str] = Field(
        default_factory=lambda: [
            "pdf", "docx", "txt", "md", "html", "json", "csv", "url"
        ]
    )

    # -------------------------------------------------------------------------
    # Web Loading Settings
    # -------------------------------------------------------------------------
    web_timeout: float = 30.0
    web_max_redirects: int = 5
    web_user_agent: str = "TrainingDataBot/0.1.0"
    web_verify_ssl: bool = True

    # -------------------------------------------------------------------------
    # Quality Evaluation Settings
    # -------------------------------------------------------------------------
    quality_threshold: float = 0.7
    enable_toxicity_check: bool = True
    enable_bias_check: bool = True
    enable_diversity_check: bool = True
    enable_coherence_check: bool = True
    enable_relevance_check: bool = True

    # -------------------------------------------------------------------------
    # Export Settings
    # -------------------------------------------------------------------------
    default_export_format: str = "jsonl"
    export_include_metadata: bool = True
    export_split_ratios: List[float] = Field(default_factory=lambda: [0.8, 0.1, 0.1])

    # -------------------------------------------------------------------------
    # Database Settings (Optional)
    # -------------------------------------------------------------------------
    database_url: Optional[str] = None
    database_echo: bool = False

    # -------------------------------------------------------------------------
    # Decodo / Web Scraping Settings (Optional)
    # -------------------------------------------------------------------------
    decodo_api_key: Optional[str] = None
    decodo_base_url: str = "https://api.decodo.com"

    # -------------------------------------------------------------------------
    # Cache Settings
    # -------------------------------------------------------------------------
    cache_enabled: bool = True
    cache_ttl: int = 3600  # 1 hour
    cache_dir: str = ".cache"

    # -------------------------------------------------------------------------
    # Rate Limiting
    # -------------------------------------------------------------------------
    rate_limit_requests: int = 60
    rate_limit_period: int = 60  # seconds


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to ensure only one Settings instance is created
    and reused across the application (singleton pattern).
    """
    return Settings()


# Global settings instance for easy import
settings = get_settings()