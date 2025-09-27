# Path from repo root: fastapi\app\crud\users.py
from __future__ import annotations
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.user import User
from app.core.security import hash_password


def get_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()


def get_by_username(db: Session, username: str) -> Optional[User]:
    return db.execute(select(User).where(User.username == username)).scalar_one_or_none()


def get_by_email(db: Session, email: str) -> Optional[User]:
    return db.execute(select(User).where(User.email == email)).scalar_one_or_none()


def create_user(
    db: Session,
    username: str,
    password: str,
    email: Optional[str] = None,
    is_superuser: bool = False,
    is_active: bool = True,
) -> User:
    u = User(
        username=username,
        email=email or None,
        password_hash=hash_password(password),  # scrypt
        is_superuser=bool(is_superuser),
        is_active=bool(is_active),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u