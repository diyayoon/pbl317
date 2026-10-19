"""Alembic migration environment.

For schema changes, MIGRATION_DATABASE_URL may point to a schema-owner account.
The web application continues to use DATABASE_URL (runtime least-privilege role).
"""
from logging.config import fileConfig
import os

from alembic import context
from flask import current_app
from sqlalchemy import create_engine

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = current_app.extensions["migrate"].db.metadata


def normalize_url(url: str) -> str:
    url = url.strip()
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    if url.startswith("postgresql+psycopg2://"):
        return "postgresql+psycopg://" + url[len("postgresql+psycopg2://"):]
    return url


migration_url = os.getenv("MIGRATION_DATABASE_URL")
if migration_url:
    migration_url = normalize_url(migration_url)


def run_migrations_offline():
    url = migration_url or current_app.config["SQLALCHEMY_DATABASE_URI"]
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_as_batch=url.startswith("sqlite"),
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    if migration_url:
        connectable = create_engine(migration_url, pool_pre_ping=True)
    else:
        connectable = current_app.extensions["migrate"].db.engine
    try:
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
                render_as_batch=connection.dialect.name == "sqlite",
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        if migration_url:
            connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
