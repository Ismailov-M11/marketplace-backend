import json
from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _fix_db_url(url: str) -> str:
    """Railway provides postgres:// or postgresql:// — convert to asyncpg dialect."""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_ENV: str = "development"
    APP_SECRET_KEY: str = "change-me"
    APP_DEBUG: bool = False
    APP_ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("APP_ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v: Any) -> list[str]:
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            # Try JSON array first: ["url1","url2"]
            if v.startswith("["):
                return json.loads(v)
            # Fallback: comma-separated string
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    # Database — raw value from env, converted via property below
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/marketplace"

    @property
    def db_url(self) -> str:
        return _fix_db_url(self.DATABASE_URL)

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "change-me-jwt-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Encryption
    BOT_TOKEN_ENCRYPTION_KEY: str = ""

    # S3
    S3_ENDPOINT_URL: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET_NAME: str = "marketplace-products"
    S3_PUBLIC_URL: str = ""

    # Sentry
    SENTRY_DSN: str = ""

    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@marketplace.uz"

    # SMS
    ESKIZ_EMAIL: str = ""
    ESKIZ_PASSWORD: str = ""
    ESKIZ_FROM: str = "marketplace"

    # Payments
    CLICK_SERVICE_ID: str = ""
    CLICK_MERCHANT_ID: str = ""
    CLICK_SECRET_KEY: str = ""
    PAYME_MERCHANT_ID: str = ""
    PAYME_SECRET_KEY: str = ""

    # Mini App
    MINIAPP_URL: str = "http://localhost:5174"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
