# Path from repo root: fastapi\app\models\user.py
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Index, UniqueConstraint, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id: int = Column(Integer, primary_key=True, index=True)
    username: str = Column(String(64), nullable=False, unique=True, index=True)
    email: Optional[str] = Column(String(255), nullable=True, unique=True, index=True)
    password_hash: str = Column(String(255), nullable=False)

    is_active: bool = Column(Boolean, nullable=False, default=True, server_default="1")
    is_superuser: bool = Column(Boolean, nullable=False, default=False, server_default="0")

    created_at: datetime = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: datetime = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("username", name="uq_users_username"),
        UniqueConstraint("email", name="uq_users_email"),
        Index("ix_users_active", "is_active"),
        Index("ix_users_superuser", "is_superuser"),
    )
