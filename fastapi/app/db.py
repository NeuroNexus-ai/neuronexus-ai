# Path from repo root: fastapi\app\db.py
from __future__ import annotations

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.engine.url import make_url
from app.core.config import get_settings


# ===== Settings =====
settings = get_settings()
RAW_URL = settings.DATABASE_URL or "sqlite:///./db/neuronexus.sqlite3"

# ===== Normalize SQLite path & ensure folder exists =====
url = make_url(RAW_URL)

# If SQLite (sync or aiosqlite) and the DB path is relative → make it absolute and ensure the folder exists.
if url.get_backend_name().startswith("sqlite"):
    db_path = url.database or "db/neuronexus.sqlite3"
    p = Path(db_path)

    if not p.is_absolute():
        # Make path absolute relative to the project root (this file lives under fastapi/app/)
        project_root = Path(__file__).resolve().parents[2]  # .../neuronexus-ai
        p = (project_root / db_path).resolve()

    p.parent.mkdir(parents=True, exist_ok=True)

    # Rebuild URL with the absolute path
    url = url.set(database=str(p))

# ===== SQLite connect args (works for sqlite and sqlite+aiosqlite) =====
connect_args = {}
if url.get_backend_name().startswith("sqlite"):
    # Needed on Windows/threaded contexts
    connect_args["check_same_thread"] = False

# ===== Engine & Session =====
engine = create_engine(
    url,               # normalized (absolute) URL if SQLite
    future=True,
    connect_args=connect_args,
    echo=False,        # set True for SQL debug
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    """Single declarative base for all models."""
    pass


# ===== FastAPI dependency =====
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ===== Optional: local dev init (without Alembic) =====
def init_db():
    """Call once in local dev if you're not running Alembic migrations."""
    Base.metadata.create_all(bind=engine)
