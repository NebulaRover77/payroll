import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import AnyHttpUrl, BaseSettings, Field, PostgresDsn, validator
from pydantic_settings import SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    env: str = Field(default="dev", description="Deployment environment")
    app_name: str = "Payroll Platform API"
    database_url: PostgresDsn | str = Field(
        default="postgresql://postgres:postgres@db:5432/payroll",
        description="Database connection string",
    )
    cors_origins: list[AnyHttpUrl] = []
    log_level: str = "INFO"
    sentry_dsn: str | None = Field(default=None, description="Sentry DSN for error monitoring")
    otlp_endpoint: str | None = Field(default=None, description="OTLP endpoint for traces/metrics")

    model_config = SettingsConfigDict(env_prefix="PAYROLL_", extra="ignore")

    @validator("cors_origins", pre=True)
    def split_origins(cls, value: str | list[AnyHttpUrl]) -> list[AnyHttpUrl]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin]
        return value

    @property
    def env_file_path(self) -> Path:
        env_specific = BASE_DIR / f".env.{self.env}"
        return env_specific if env_specific.exists() else BASE_DIR / ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings(_env_file=get_settings_env_file())


def get_settings_env_file() -> str | None:
    """Resolve environment-specific env file if it exists."""
    env = os.getenv("PAYROLL_ENV", "dev")
    env_file = BASE_DIR / f".env.{env}"
    default_file = BASE_DIR / ".env"
    if env_file.exists():
        return str(env_file)
    if default_file.exists():
        return str(default_file)
    return None


settings = get_settings()
