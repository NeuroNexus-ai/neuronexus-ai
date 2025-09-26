from __future__ import annotations
from sqlalchemy.orm import Session
from sqlalchemy import select
from passlib.hash import bcrypt
from app.models.user import User

def get_user_by_username(db: Session, username: str) -> User | None:
    return db.execute(select(User).where(User.username == username)).scalar_one_or_none()

def create_user(db: Session, username: str, password: str, is_superuser: bool = False) -> User:
    u = User(username=username, password_hash=bcrypt.hash(password), is_superuser=is_superuser, is_active=True)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u

def verify_password(plain: str, password_hash: str) -> bool:
    return bcrypt.verify(plain, password_hash)
