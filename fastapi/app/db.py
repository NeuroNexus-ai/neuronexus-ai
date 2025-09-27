# Path from repo root: fastapi\app\db.py
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import get_settings

settings = get_settings()

DATABASE_URL = settings.DATABASE_URL or "sqlite:///./db/neuronexus.sqlite3"
# SQLite on Windows needs this flag
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    future=True,
    connect_args=connect_args,
    echo=False,  # اجعله True لو بدك لوج SQL
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

class Base(DeclarativeBase):
    """Single declarative base for all models."""
    pass