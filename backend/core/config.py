"""
Configuration management using Pydantic Settings.
Supports environment-specific configs (development, testing, production).
"""

from functools import lru_cache
from typing import Any, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Base settings class with common configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    ENVIRONMENT: Literal["development", "testing", "production"] = "development"

    # Application
    APP_NAME: str = "ContriVerse"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    SECRET_KEY: str

    # API
    API_V1_PREFIX: str = "/api/v1"
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # Database - NeonDB with Prisma
    DATABASE_URL: str  # Pooled connection for application
    DIRECT_DATABASE_URL: str  # Direct connection for migrations

    @field_validator("DATABASE_URL", "DIRECT_DATABASE_URL")
    @classmethod
    def validate_database_urls(cls, v: str, info) -> str:
        """Ensure database URLs are set and use PostgreSQL."""
        if not v:
            field_name = info.field_name
            raise ValueError(
                f"{field_name} must be set. "
                "See docs/NEONDB_SETUP.md for setup instructions."
            )
        if not v.startswith("postgresql://"):
            raise ValueError(f"{info.field_name} must be a PostgreSQL connection string")
        return v

    # Redis
    REDIS_URL: str

    # Celery
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: Literal["json", "console"] = "json"

    # JWT
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # GitHub Integration
    GITHUB_WEBHOOK_SECRET: str
    GITHUB_APP_ID: Optional[str] = None
    GITHUB_APP_PRIVATE_KEY: Optional[str] = None

    # API Configuration
    API_BASE_URL: str = "http://localhost:8000"  # Base URL for webhooks

    @field_validator("GITHUB_WEBHOOK_SECRET")
    @classmethod
    def validate_webhook_secret(cls, v: str) -> str:
        """Ensure webhook secret is set."""
        if not v:
            raise ValueError("GITHUB_WEBHOOK_SECRET must be set for webhook security")
        return v

    # GitHub OAuth (required for authentication)
    GITHUB_CLIENT_ID: str
    GITHUB_CLIENT_SECRET: str
    GITHUB_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/github/callback"

    @field_validator("GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET")
    @classmethod
    def validate_github_oauth(cls, v: str, info) -> str:
        """Ensure GitHub OAuth credentials are set."""
        if not v:
            field_name = info.field_name
            raise ValueError(
                f"{field_name} must be set. "
                "Register a GitHub OAuth App at https://github.com/settings/developers"
            )
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Ensure SECRET_KEY is set and not a placeholder."""
        if not v or v == "your-secret-key-here-change-in-production":
            raise ValueError(
                "SECRET_KEY must be set to a secure value. "
                "Generate one with: openssl rand -hex 32"
            )
        return v

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


class DevelopmentSettings(Settings):
    """Development environment settings."""

    DEBUG: bool = True
    DB_ECHO: bool = True
    LOG_FORMAT: Literal["json", "console"] = "console"


class TestingSettings(Settings):
    """Testing environment settings."""

    DEBUG: bool = True
    DB_ECHO: bool = False
    LOG_FORMAT: Literal["json", "console"] = "console"


class ProductionSettings(Settings):
    """Production environment settings."""

    DEBUG: bool = False
    DB_ECHO: bool = False
    LOG_FORMAT: Literal["json", "console"] = "json"


@lru_cache
def get_settings() -> Settings:
    """
    Get settings instance based on ENVIRONMENT variable.
    Cached to avoid re-reading environment variables.
    """
    import os

    environment = os.getenv("ENVIRONMENT", "development").lower()

    settings_map = {
        "development": DevelopmentSettings,
        "testing": TestingSettings,
        "production": ProductionSettings,
    }

    settings_class = settings_map.get(environment, DevelopmentSettings)
    return settings_class()


# Global settings instance
settings = get_settings()
