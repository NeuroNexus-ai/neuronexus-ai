# Path from repo root: fastapi\app\core\security.py

from __future__ import annotations
from datetime import datetime, timedelta
import os, base64, hashlib, hmac, secrets, jwt

JWT_SECRET = os.getenv("APP_JWT_SECRET", secrets.token_urlsafe(32))
JWT_ALG = "HS256"
ACCESS_TTL_MIN = int(os.getenv("APP_ACCESS_TTL_MIN", "30"))
REFRESH_TTL_DAYS = int(os.getenv("APP_REFRESH_TTL_DAYS", "7"))

def create_access_token(sub: str, roles: list[str]) -> str:
    now = datetime.utcnow()
    payload = {"sub": sub, "roles": roles, "iat": int(now.timestamp()),
               "exp": int((now + timedelta(minutes=ACCESS_TTL_MIN)).timestamp())}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def create_refresh_token(sub: str) -> tuple[str, datetime]:
    now = datetime.utcnow()
    exp = now + timedelta(days=REFRESH_TTL_DAYS)
    payload = {"sub": sub, "type": "refresh", "iat": int(now.timestamp()),
               "exp": int(exp.timestamp())}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG), exp