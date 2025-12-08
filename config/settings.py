"""Settings and configuration management."""
import os
from typing import Optional
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # GCP Configuration
    gcp_project_id: Optional[str] = Field(
        default=None,
        env="GOOGLE_CLOUD_PROJECT",
        description="GCP Project ID"
    )
    bigquery_dataset: str = Field(
        default="bi_assessment",
        env="BIGQUERY_DATASET",
        description="BigQuery dataset name"
    )
    gcs_bucket: Optional[str] = Field(
        default=None,
        env="GCS_BUCKET",
        description="GCS bucket name for metadata files"
    )
    
    # LLM Configuration
    llm_model: str = Field(
        default="claude-3-5-sonnet-20241022",
        env="LLM_MODEL",
        description="LLM model name (Claude)"
    )
    anthropic_api_key: Optional[str] = Field(
        default=None,
        env="ANTHROPIC_API_KEY",
        description="Anthropic API key for Claude"
    )
    gemini_model: str = Field(
        default="gemini-2.5-flash",
        env="GEMINI_MODEL",
        description="Gemini model name for Vertex AI"
    )
    vertex_ai_location: str = Field(
        default="us-central1",
        env="VERTEX_AI_LOCATION",
        description="Vertex AI location"
    )
    
    # Application Configuration
    log_level: str = Field(
        default="INFO",
        env="LOG_LEVEL",
        description="Logging level"
    )
    max_retries: int = Field(
        default=3,
        env="MAX_RETRIES",
        description="Maximum retry attempts for API calls"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


_settings: Optional[Settings] = None


def load_settings() -> Settings:
    """Load and return application settings."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def get_settings() -> Settings:
    """Get current settings instance."""
    if _settings is None:
        return load_settings()
    return _settings

