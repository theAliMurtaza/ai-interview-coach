"""
Alembic environment.

Uses DATABASE_URL_SYNC (psycopg2, not asyncpg) because Alembic's
migration runner is synchronous — see .env.example. Imports
app.models so autogenerate (`alembic revision --autogenerate`) sees
every implemented model's metadata.
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, text

import app.models  # noqa: F401 — registers all implemented models
from alembic import context
from app.core.config import settings
from app.core.database import Base
from app.core.database_urls import sync_database_url

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option(
    "sqlalchemy.url",
    sync_database_url(settings.DATABASE_URL_SYNC or settings.DATABASE_URL).replace("%", "%%"),
)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        # Free hosting runs migrations at startup. Serialize overlapping deploys
        # on a direct PostgreSQL connection before Alembic checks the revision.
        connection.execute(text("SET lock_timeout = '60s'"))
        connection.execute(text("SELECT pg_advisory_lock(731842090)"))
        connection.commit()
        try:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
        finally:
            connection.rollback()
            connection.execute(text("SELECT pg_advisory_unlock(731842090)"))
            connection.commit()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
