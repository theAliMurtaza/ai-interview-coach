"""
Centralized configuration.

Every setting is read from the environment (see .env.example). Nothing
in this file should ever hold a real secret — defaults here are safe,
non-functional placeholders only.
"""

from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.database_urls import async_database_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_NAME: str = "Console API"
    APP_ENV: Literal["development", "test", "staging", "production"] = "development"
    DEBUG: bool = False
    SECRET_KEY: str
    API_V1_PREFIX: str = "/api/v1"
    BACKEND_CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # Auth
    JWT_ALGORITHM: Literal["HS256"] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    GOOGLE_OAUTH_CLIENT_ID: str = ""

    # Database
    DATABASE_URL: str
    DATABASE_URL_SYNC: str = ""
    DATABASE_POOL_SIZE: int = Field(default=2, ge=1, le=20)
    DATABASE_MAX_OVERFLOW: int = Field(default=3, ge=0, le=20)
    RENDER_EXTERNAL_HOSTNAME: str = ""

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # LLM
    LLM_PROVIDER: Literal["openai", "anthropic", "local"] = "openai"
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"

    # Speech
    STT_PROVIDER: Literal["openai_whisper"] = "openai_whisper"
    TTS_PROVIDER: Literal["openai"] = "openai"

    # Storage
    STORAGE_ENDPOINT_URL: str = ""
    STORAGE_ACCESS_KEY_ID: str = ""
    STORAGE_SECRET_ACCESS_KEY: str = ""
    STORAGE_BUCKET_NAME: str = "console-uploads"
    STORAGE_REGION: str = "auto"

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_ID_PRO: str = ""

    # n8n

    # Observability
    SENTRY_DSN: str = ""
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""

    AI_ENABLED: bool = False
    LOCAL_LLM_BASE_URL: str = ""
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    LOCAL_STORAGE_DIR: str = "uploads"
    MAX_UPLOAD_BYTES: int = Field(default=10 * 1024 * 1024, ge=1024, le=25 * 1024 * 1024)
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = Field(default=120, ge=1)
    AUTH_RATE_LIMIT_PER_MINUTE: int = Field(default=10, ge=1)
    WEBHOOK_RATE_LIMIT_PER_MINUTE: int = Field(default=300, ge=1)
    BILLING_RETURN_URL: str = "http://localhost:5173/billing"
    N8N_WEBHOOK_SECRET: str = ""
    ALLOWED_HOSTS: list[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1", "test"])

    @field_validator("DATABASE_URL")
    @classmethod
    def normalize_database_url(cls, value):
        return async_database_url(value)

    @model_validator(mode="after")
    def validate_deployment(self):
        if (
            self.RENDER_EXTERNAL_HOSTNAME
            and self.RENDER_EXTERNAL_HOSTNAME not in self.ALLOWED_HOSTS
        ):
            self.ALLOWED_HOSTS = [*self.ALLOWED_HOSTS, self.RENDER_EXTERNAL_HOSTNAME]
        if self.ACCESS_TOKEN_EXPIRE_MINUTES <= 0 or self.REFRESH_TOKEN_EXPIRE_DAYS <= 0:
            raise ValueError("Token lifetimes must be positive")
        if self.APP_ENV in {"production", "staging"}:
            placeholder = any(
                marker in self.SECRET_KEY.lower()
                for marker in ("change-me", "replace-with", "test-only", "example", "your-secret")
            )
            if (
                self.DEBUG
                or len(self.SECRET_KEY) < 32
                or placeholder
                or len(set(self.SECRET_KEY)) < 8
            ):
                raise ValueError(
                    "Production requires DEBUG=false and a random SECRET_KEY >=32 chars"
                )
            if not self.DATABASE_URL.startswith("postgresql+asyncpg://"):
                raise ValueError("Production requires PostgreSQL with asyncpg")
            if not self.RATE_LIMIT_ENABLED or not self.REDIS_URL:
                raise ValueError("Production requires Redis rate limiting")
            if self.STORAGE_BACKEND != "s3":
                raise ValueError("Production requires private S3-compatible storage")
            if not self.ALLOWED_HOSTS or any(
                not host or any(char in host for char in "*/:@ ") for host in self.ALLOWED_HOSTS
            ):
                raise ValueError("Production requires explicit ALLOWED_HOSTS")
            if not self.BACKEND_CORS_ORIGINS or any(
                not self._https_origin(origin) for origin in self.BACKEND_CORS_ORIGINS
            ):
                raise ValueError("Production CORS origins must be explicit HTTPS origins")
            if self.STORAGE_ENDPOINT_URL and urlsplit(self.STORAGE_ENDPOINT_URL).scheme != "https":
                raise ValueError("Production storage endpoints must use HTTPS")
        if self.AI_ENABLED:
            configured = {
                "openai": self.OPENAI_API_KEY,
                "anthropic": self.ANTHROPIC_API_KEY,
                "local": self.LOCAL_LLM_BASE_URL,
            }
            if not configured[self.LLM_PROVIDER]:
                raise ValueError("AI_ENABLED requires credentials for the selected provider")
        return self

    @staticmethod
    def _https_origin(origin: str) -> bool:
        parsed = urlsplit(origin)
        return bool(
            parsed.scheme == "https"
            and parsed.hostname
            and "*" not in parsed.netloc
            and not parsed.username
            and not parsed.password
            and not parsed.path
            and not parsed.query
            and not parsed.fragment
        )


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton — import this, not Settings() directly."""
    return Settings()


settings = get_settings()
