# app/db.py
from __future__ import annotations
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from pathlib import Path
from app.core.config import get_settings

st = get_settings()

def _resolve_sqlite_url(url: str) -> str:
    if url.startswith("sqlite:///./"):
        base = Path(__file__).resolve().parents[1]  # fastapi/
        db_path = base / url.replace("sqlite:///./", "")
        return f"sqlite:///{db_path.as_posix()}"
    return url

SQLALCHEMY_DATABASE_URL = _resolve_sqlite_url(st.DATABASE_URL)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL.replace("+aiosqlite", ""),
    connect_args={"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {},
    future=True,
)

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _sqlite_on_connect(dbapi_conn, _):  # noqa: ANN001
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL;")
        cur.execute("PRAGMA synchronous=NORMAL;")
        cur.execute("PRAGMA foreign_keys=ON;")
        cur.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
