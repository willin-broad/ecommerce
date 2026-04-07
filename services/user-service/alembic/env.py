"""Alembic environment configuration.

Loads the database URL from the application's Settings class (pydantic-settings)
so credentials are never hardcoded. All models are imported here so Alembic
can auto-detect schema changes.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from src.config import get_settings
from src.database import Base

# Import all models so Alembic detects them in Base.metadata
import src.models.user  # noqa: F401

config = context.config
settings = get_settings()

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no DB connection needed, outputs SQL)."""
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connects to DB and applies changes)."""
    connectable = create_engine(settings.DATABASE_URL)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
