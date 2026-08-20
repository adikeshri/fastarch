"""Strongly-typed application configuration (PRD §27).

All configuration is environment-driven; nothing here contains a real
secret — ``.env.example`` documents every variable with a safe placeholder.
Nested groups (``DATABASE__URL``, ``REDIS__URL``, ...) use pydantic-settings'
``env_nested_delimiter`` so each concern gets its own typed sub-model while
still loading from a flat environment / ``.env`` file. See
``docs/configuration.md`` for the full reference and per-environment
guidance (development / testing / staging / production).
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import BaseModel, Field, PostgresDsn, RedisDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"

    @property
    def is_production_like(self) -> bool:
        return self in {Environment.STAGING, Environment.PRODUCTION}


class DatabaseSettings(BaseModel):
    url: PostgresDsn = PostgresDsn("postgresql+asyncpg://fastarch:fastarch@localhost:5432/fastarch")
    pool_size: int = 10
    max_overflow: int = 10
    pool_timeout_seconds: int = 30
    echo: bool = False


class RedisSettings(BaseModel):
    url: RedisDsn = RedisDsn("redis://localhost:6379/0")
    max_connections: int = 20


class AuthSettings(BaseModel):
    jwt_secret: SecretStr = SecretStr("change-me-in-every-real-environment")
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "fastarch"
    jwt_audience: str = "fastarch-api"
    access_token_ttl_minutes: int = 30


class ObservabilitySettings(BaseModel):
    service_name: str = "fastarch"
    otlp_endpoint: str | None = None
    traces_enabled: bool = True
    metrics_enabled: bool = True
    log_level: str = "INFO"
    json_logs: bool = True


class SecuritySettings(BaseModel):
    cors_allow_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    trusted_hosts: list[str] = Field(default_factory=lambda: ["*"])


class Settings(BaseSettings):
    """Root settings object. Construct via :func:`get_settings` (cached singleton)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    environment: Environment = Environment.DEVELOPMENT
    api_prefix: str = "/api"
    project_name: str = "fastarch"
    debug: bool = False

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)

    outbox_relay_interval_seconds: float = 1.0
    outbox_relay_batch_size: int = 100
    outbox_max_attempts: int = 10


@lru_cache
def get_settings() -> Settings:
    return Settings()
