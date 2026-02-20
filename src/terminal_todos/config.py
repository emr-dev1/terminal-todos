"""Configuration management for Terminal Todos."""

import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API Keys
    openai_api_key: str = Field(..., description="OpenAI API key for LLM features")

    # Paths
    data_dir: Path = Field(
        default_factory=lambda: Path.home() / ".terminal-todos" / "data",
        description="Directory for storing application data",
    )

    @property
    def db_path(self) -> Path:
        """Path to SQLite database file."""
        return self.data_dir / "todos.db"

    @property
    def chroma_path(self) -> Path:
        """Path to ChromaDB persistence directory."""
        return self.data_dir / "chroma"

    # Models
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2",
        description="Sentence transformers model for embeddings",
    )

    llm_model: str = Field(
        default="gpt-4o",
        description="OpenAI model for agent and extraction",
    )

    # User Info
    user_name: str = Field(
        default="User",
        description="Your name for filtering out from captured notes (e.g., 'Ed Robinson')"
    )

    # Behavior
    max_todos_display: int = Field(
        default=100, description="Maximum number of todos to display at once"
    )

    search_results_limit: int = Field(
        default=10, description="Maximum number of search results to return"
    )

    # Debugging
    verbose_logging: bool = Field(
        default=False,
        description="Enable verbose error logging and debugging output"
    )

    # Arize AX Tracing
    enable_arize_tracing: bool = Field(
        default=False,
        description="Enable Arize AX tracing for agent observability and debugging"
    )

    arize_space_id: Optional[str] = Field(
        default=None,
        description="Arize Space ID for tracing"
    )

    arize_api_key: Optional[str] = Field(
        default=None,
        description="Arize API Key for tracing"
    )

    arize_project_name: str = Field(
        default="terminal-todos",
        description="Project name for Arize traces"
    )

    def ensure_data_dir(self) -> None:
        """Ensure data directory exists."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_path.mkdir(parents=True, exist_ok=True)


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.ensure_data_dir()
    return _settings


def reset_settings() -> None:
    """Reset the global settings instance (useful for testing)."""
    global _settings
    _settings = None
