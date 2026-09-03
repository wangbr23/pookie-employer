"""Application configuration."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "test", "production"]


def _parse_origins(value: str) -> list[str]:
    """Split a comma-separated origins string, trimming whitespace and empties."""
    return [origin.strip() for origin in value.split(",") if origin.strip()]


class Settings(BaseSettings):
    """Typed settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Pookie Employer Backend"
    environment: Environment = Field(default="development", alias="PYTHON_ENV")
    database_url: str = Field(alias="DATABASE_URL")
    secret_key: SecretStr = Field(alias="SECRET_KEY")
    api_secret: SecretStr = Field(alias="API_SECRET", min_length=1)
    cors_allowed_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        alias="CORS_ALLOWED_ORIGINS",
    )

    @field_validator("cors_allowed_origins")
    @classmethod
    def _reject_wildcard_origin(cls, value: str) -> str:
        """Reject "*" so a config typo can't combine with allow_credentials to open CORS to any origin."""
        if "*" in _parse_origins(value):
            raise ValueError(
                "CORS_ALLOWED_ORIGINS must not contain '*'; list explicit origins instead."
            )
        return value

    @property
    def cors_origins(self) -> list[str]:
        """Return configured CORS origins, excluding empty entries."""
        return _parse_origins(self.cors_allowed_origins)


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()  # type: ignore[call-arg]
