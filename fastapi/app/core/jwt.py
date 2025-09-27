# app/core/jwt.py
from __future__ import annotations
from datetime import datetime, timedelta
import jwt
from app.core.config import get_settings

st = get_settings()

def _encode(payload: dict, ttl: timedelta) -> str:
    now = datetime.utcnow()
    data = payload | {"iat": now, "exp": now + ttl}
    return jwt.encode(data, st.JWT_SECRET, algorithm=st.JWT_ALGORITHM)

def create_access_token(sub: str, roles: list[str]) -> str:
    ttl = timedelta(minutes=st.JWT_EXPIRE_MINUTES or 60)  # افتراضي 60 دقيقة لو None
    return _encode({"sub": sub, "scope": "access", "roles": roles}, ttl)

def create_refresh_token(sub: str) -> str:
    days = 30
    return _encode({"sub": sub, "scope": "refresh"}, timedelta(days=days))

def decode_token(token: str) -> dict:
    return jwt.decode(token, st.JWT_SECRET, algorithms=[st.JWT_ALGORITHM])
