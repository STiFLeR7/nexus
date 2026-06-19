"""Nexus configuration management.

Loads configuration from environment variables, ``.env`` files, and
``config/settings.yaml`` using Pydantic Settings.  A cached
``get_settings()`` accessor ensures the settings object is built once.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# ---------------------------------------------------------------------------
# Nested configuration models
# ---------------------------------------------------------------------------

class DiscordConfig(BaseModel):
    """Discord bot and channel configuration."""

    token: str = ""
    guild_id: int = 0
    owner_ids: list[int] = Field(default_factory=list)
    command_channel: str = "nexus-commands"
    log_channel: str = "nexus-logs"
    alert_channel: str = "nexus-alerts"
    report_channel: str = "nexus-reports"


class EmailConfig(BaseModel):
    """Email / SMTP configuration."""

    provider: str = "smtp"
    smtp_host: str = "localhost"
    smtp_port: int = 587
    username: str = ""
    password: str = ""
    from_address: str = ""
    to_address: str = ""
    use_tls: bool = True


class OpenRouterConfig(BaseModel):
    """OpenRouter LLM gateway configuration."""

    api_key: str = ""
    primary_model: str = "google/gemini-2.5-pro"
    fallback_models: list[str] = Field(
        default_factory=lambda: [
            "anthropic/claude-sonnet-4",
            "google/gemini-2.5-flash",
        ]
    )
    base_url: str = "https://openrouter.ai/api/v1"


class DatabaseConfig(BaseModel):
    """Database connection configuration."""

    url: str = "sqlite+aiosqlite:///./data/nexus.db"
    echo: bool = False


class ExecutionConfig(BaseModel):
    """Timeout thresholds for execution runners (in seconds)."""

    research_timeout: int = 900
    gemini_timeout: int = 1800
    claude_timeout: int = 2700
    hard_limit: int = 3600


class LoggingConfig(BaseModel):
    """Structured logging configuration."""

    level: str = "INFO"
    format: str = "json"


# ---------------------------------------------------------------------------
# Root settings
# ---------------------------------------------------------------------------

def _load_yaml_settings(yaml_path: Path) -> dict[str, Any]:
    """Load settings from a YAML file if it exists."""
    if yaml_path.exists():
        with open(yaml_path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
            if isinstance(data, dict):
                return data
    return {}


class NexusSettings(BaseSettings):
    """Top-level Nexus application settings.

    Sources (highest to lowest priority):
      1. Environment variables / ``.env``
      2. ``config/settings.yaml``
      3. Field defaults
    """

    model_config = SettingsConfigDict(
        env_prefix="NEXUS_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Metadata
    version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False

    # Subsystem configs
    discord: DiscordConfig = Field(default_factory=DiscordConfig)
    email: EmailConfig = Field(default_factory=EmailConfig)
    openrouter: OpenRouterConfig = Field(default_factory=OpenRouterConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @classmethod
    def from_yaml_and_env(cls, yaml_path: Path | None = None) -> NexusSettings:
        """Construct settings merging YAML defaults with env overrides."""
        path = yaml_path or Path("config/settings.yaml")
        yaml_data = _load_yaml_settings(path)
        return cls(**yaml_data)


@lru_cache(maxsize=1)
def get_settings() -> NexusSettings:
    """Return the cached application settings singleton."""
    return NexusSettings.from_yaml_and_env()
