import logging
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

_INSECURE_DEFAULT = "insecure-default-change-in-production"


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    # Application
    APP_ENV: str = "development"
    PORT: int = 3001

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "users_db"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "changeme"

    # JWT
    JWT_SECRET: str = _INSECURE_DEFAULT
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # RabbitMQ
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672"

    # Email (SMTP stub — activate in Step 4)
    SMTP_HOST: str = "smtp.example.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@ecommerce.local"

    # App base URL used in email links
    APP_BASE_URL: str = "http://localhost:3001"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @model_validator(mode="after")
    def validate_secrets(self) -> "Settings":
        """Enforce JWT_SECRET security rules at startup."""
        if len(self.JWT_SECRET) < 32:
            raise ValueError(
                "JWT_SECRET must be at least 32 characters long. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        if self.APP_ENV == "production" and self.JWT_SECRET == _INSECURE_DEFAULT:
            raise ValueError(
                "JWT_SECRET must be explicitly set in production — refusing to start. "
                "Generate a secure key: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        if self.JWT_SECRET == _INSECURE_DEFAULT:
            logger.warning(
                "⚠️  JWT_SECRET is using the insecure default. "
                "Set JWT_SECRET in your .env file before deploying."
            )
        return self

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
