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
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# ---------------------------------------------------------------------------
# Nested configuration models
# ---------------------------------------------------------------------------

class DiscordChannels(BaseModel):
    """Channel mapping for Discord bot routing."""

    inbox: str = "nexus-commands"
    tasks: str = "nexus-timeline"
    approvals: str = "nexus-approvals"
    execution_log: str = Field("nexus-logs", alias="execution-log")
    research: str = "nexus-research"
    summaries: str = "nexus-reports"
    alerts: str = "nexus-alerts"

    model_config = ConfigDict(populate_by_name=True)


class DiscordConfig(BaseModel):
    """Discord bot and channel configuration."""

    token: str = ""
    guild_id: int = 0
    owner_ids: list[int] = Field(default_factory=list)
    channels: DiscordChannels = Field(default_factory=DiscordChannels)


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

        import os

        from dotenv import load_dotenv
        load_dotenv()

        # Map environment overrides directly for convenience in local development
        if "discord" not in yaml_data:
            yaml_data["discord"] = {}

        if os.getenv("DISCORD_BOT_TOKEN"):
            yaml_data["discord"]["token"] = os.getenv("DISCORD_BOT_TOKEN")
        import contextlib
        if os.getenv("DISCORD_GUILD_ID"):
            with contextlib.suppress(ValueError):
                yaml_data["discord"]["guild_id"] = int(os.getenv("DISCORD_GUILD_ID", "0"))

        # Load owner IDs if specified as comma-separated or JSON list
        owners_env = os.getenv("DISCORD_OWNERS") or os.getenv("NEXUS_DISCORD__OWNER_IDS")
        if owners_env:
            with contextlib.suppress(ValueError):
                yaml_data["discord"]["owner_ids"] = [int(x.strip()) for x in owners_env.split(",")]

        if "openrouter" not in yaml_data:
            yaml_data["openrouter"] = {}

        if os.getenv("OPENROUTER_API_KEY"):
            yaml_data["openrouter"]["api_key"] = os.getenv("OPENROUTER_API_KEY")

        return cls(**yaml_data)


@lru_cache(maxsize=1)
def get_settings() -> NexusSettings:
    """Return the cached application settings singleton."""
    return NexusSettings.from_yaml_and_env()
