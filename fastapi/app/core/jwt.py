# Path from repo root: fastapi\app\core\jwt.py
from __future__ import annotations

import os
import uuid
import datetime as dt
from typing import Any, Dict
import jwt


JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-prod")
JWT_ALG = "HS256"
ACCESS_MIN = int(os.getenv("ACCESS_MIN", "30"))
REFRESH_DAYS = int(os.getenv("REFRESH_DAYS", "7"))


def make_token(payload: Dict[str, Any], minutes: int | None = None, days: int | None = None) -> str:
    """Create a signed JWT with exp/iat/nbf and a unique jti."""
    now = dt.datetime.utcnow()
    if minutes is None and days is None:
        raise ValueError("Either minutes or days must be provided")
    exp = now + (dt.timedelta(minutes=minutes) if minutes else dt.timedelta(days=days))
    claims = {
        **payload,
        "exp": exp,
        "iat": now,
        "nbf": now,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(claims, JWT_SECRET, algorithm=JWT_ALG)


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT; raises on invalid/expired."""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
