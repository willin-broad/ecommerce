from functools import lru_cache
from pydantic_settings import BaseSettings


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
    JWT_SECRET: str = "insecure-default-change-in-production"
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

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
