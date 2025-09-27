# Path from repo root: fastapi\alembic\env.py
from __future__ import annotations

from logging.config import fileConfig
import sys, pathlib
from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure fastapi/ is on sys.path
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

# Import ONLY what's needed (avoid importing app.core top-level side-effects)
from app.models.user import Base
from app.core.config import get_settings

config = context.config

# Read DATABASE_URL from app settings (strip +aiosqlite for sync engine)
st = get_settings()
config.set_main_option("sqlalchemy.url", st.DATABASE_URL.replace("+aiosqlite", ""))

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

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
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
