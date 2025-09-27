# Path from repo root: fastapi\app\crud\users.py
from __future__ import annotations
from typing import Optional, Sequence
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.user import User
from app.core.security import hash_password, verify_password
from app.schemas.user import UserCreate, UserUpdate

def get_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.get(User, user_id)

def get_by_username(db: Session, username: str) -> Optional[User]:
    stmt = select(User).where(User.username == username)
    return db.execute(stmt).scalar_one_or_none()

def get_by_email(db: Session, email: str) -> Optional[User]:
    stmt = select(User).where(User.email == email)
    return db.execute(stmt).scalar_one_or_none()

def list_users(db: Session, skip: int = 0, limit: int = 50) -> Sequence[User]:
    stmt = select(User).offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()

def create_user(db: Session, data: UserCreate) -> User:
    if get_by_username(db, data.username):
        raise ValueError("Username already exists")
    if data.email and get_by_email(db, data.email):
        raise ValueError("Email already exists")
    u = User(
        username=data.username,
        email=data.email,
        password_hash=hash_password(data.password),
        is_active=data.is_active,
        is_superuser=data.is_superuser,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u

def update_user(db: Session, user: User, data: UserUpdate) -> User:
    if data.username is not None:
        user.username = data.username
    if data.email is not None:
        user.email = data.email
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.is_superuser is not None:
        user.is_superuser = data.is_superuser
    if data.password:
        user.password_hash = hash_password(data.password)

    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def delete_user(db: Session, user: User) -> None:
    db.delete(user)
    db.commit()

def authenticate(db: Session, username: str, password: str) -> Optional[User]:
    u = get_by_username(db, username)
    if not u or not u.is_active:
        return None
    return u if verify_password(password, u.password_hash) else None
