# app/bootstrap.py
from __future__ import annotations

import os
from sqlalchemy.orm import Session
from sqlalchemy import inspect

from app.db import SessionLocal, engine, Base
from app.models.user import User
from app.core.security import hash_password

ADMIN_USER_ENV   = "APP_ADMIN_USER"
ADMIN_PASS_ENV   = "APP_ADMIN_PASS"
ADMIN_EMAIL_ENV  = "APP_ADMIN_EMAIL"

def _env(var: str, default: str | None = None) -> str | None:
    val = os.getenv(var)
    return val if (val is not None and val.strip() != "") else default

def create_admin_if_missing() -> None:
    db: Session = SessionLocal()
    try:
        # تأكد من وجود جدول users — وإن لم يوجد، أنشئ الجداول
        insp = inspect(engine)
        if not insp.has_table("users"):
            Base.metadata.create_all(bind=engine)

        # هل يوجد أي superuser؟
        exists = db.query(User).filter(User.is_superuser.is_(True)).first()
        if exists:
            print("ℹ️ [bootstrap] Superuser already exists → skip")
            return

        username = _env(ADMIN_USER_ENV,  "admin")
        password = _env(ADMIN_PASS_ENV,  "admin123")
        email    = _env(ADMIN_EMAIL_ENV, "admin@example.com")

        if not username or not password:
            print("⚠️ [bootstrap] Missing ADMIN_USER/ADMIN_PASS → skip creating admin")
            return

        u = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            is_superuser=True,
            is_active=True,
        )
        db.add(u)
        db.commit()
        print(f"✅ [bootstrap] Superuser created: {username}")

    except Exception as e:
        print(f"❌ [bootstrap] Failed to create admin: {e}")
        db.rollback()
    finally:
        db.close()
