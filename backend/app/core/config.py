import os
from functools import lru_cache
from pathlib import Path

from pydantic import AnyHttpUrl, Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PAYROLL_",
        extra="ignore",
    )

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

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, v):
        if v is None or v == "":
            return []
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v


def get_settings_env_file() -> str | None:
    env = os.getenv("PAYROLL_ENV", "dev")
    env_file = BASE_DIR / f".env.{env}"
    default_file = BASE_DIR / ".env"
    if env_file.exists():
        return str(env_file)
    if default_file.exists():
        return str(default_file)
    return None


@lru_cache
def get_settings() -> Settings:
    return Settings(_env_file=get_settings_env_file())


settings = get_settings()
