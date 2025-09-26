# app/api/router_auth.py
from __future__ import annotations

import json
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------- Models ----------
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class User(BaseModel):
    username: str
    is_authenticated: bool = False


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ---------- User store (from settings) ----------
def _verify_password(plain: str, stored: str) -> bool:
    """
    If stored value looks like a bcrypt hash (starts with '$2'), verify with passlib[bcrypt].
    Otherwise, treat it as plaintext and compare in constant time.
    """
    if stored.startswith("$2"):
        try:
            from passlib.hash import bcrypt
            return bcrypt.verify(plain, stored)
        except Exception:
            # Fail closed if bcrypt backend not available
            return False
    return secrets.compare_digest(plain, stored)


def _load_users_from_settings() -> Dict[str, str]:
    """
    Build a username -> secret map from settings.
    Supports:
      - AUTH_USERS_JSON='{"admin":"<bcrypt-or-plain>", "alice":"..."}'
      - APP_ADMIN_USER + (APP_ADMIN_PASS or APP_ADMIN_BCRYPT)
      - ADMIN_USER + (ADMIN_PASSWORD or ADMIN_BCRYPT)  # aliases
    """
    st = get_settings()
    users: Dict[str, str] = {}

    # 1) AUTH_USERS_JSON (preferred for multiple users)
    auth_users_json: Optional[str] = getattr(st, "AUTH_USERS_JSON", None)
    if auth_users_json:
        try:
            parsed = json.loads(auth_users_json)
            if isinstance(parsed, dict):
                # keep only string:string entries
                for k, v in parsed.items():
                    if isinstance(k, str) and isinstance(v, str) and k.strip():
                        users[k.strip()] = v.strip()
        except Exception:
            # ignore malformed JSON
            pass

    # 2) Single admin via APP_* keys
    admin_user = (
        getattr(st, "APP_ADMIN_USER", None)
        or getattr(st, "ADMIN_USER", None)
    )
    admin_pass = (
        getattr(st, "APP_ADMIN_PASS", None)
        or getattr(st, "ADMIN_PASSWORD", None)
    )
    admin_bcrypt = (
        getattr(st, "APP_ADMIN_BCRYPT", None)
        or getattr(st, "ADMIN_BCRYPT", None)
    )
    if admin_user:
        # prefer bcrypt if provided, else plaintext pass
        secret = (admin_bcrypt or admin_pass)
        if isinstance(secret, str) and secret.strip():
            users[admin_user.strip()] = secret.strip()

    # 3) Fallback for dev if nothing provided — OPTIONAL
    if not users:
        # Comment-out this fallback if you don't want any default.
        users["admin"] = "$2b$12$6qgc4A4Sb77FhYcbOsi/U.LLsiz8WzADHax2p7qW1NillAkQ4YT3m"  # bcrypt("admin123")

    return users


_USERS = _load_users_from_settings()


# ---------- Key loading ----------
def _load_sign_keys():
    """
    Returns (signing_key, verify_key, alg).
    - HS*  -> use settings.JWT_SECRET for both sign & verify
    - RS*/ES* -> read private/public key files
    """
    st = get_settings()
    alg = st.JWT_ALGORITHM.upper().strip()

    if alg.startswith("HS"):
        if not st.JWT_SECRET:
            raise RuntimeError("APP_JWT_SECRET is required for HS* algorithms")
        return st.JWT_SECRET, st.JWT_SECRET, alg

    # Asymmetric: RS*, ES*
    if not st.JWT_PRIVATE_KEY_PATH or not st.JWT_PUBLIC_KEY_PATH:
        raise RuntimeError(
            "APP_JWT_PRIVATE_KEY_PATH and APP_JWT_PUBLIC_KEY_PATH are required for RS*/ES* algorithms"
        )

    priv = Path(st.JWT_PRIVATE_KEY_PATH).read_text(encoding="utf-8")
    pub = Path(st.JWT_PUBLIC_KEY_PATH).read_text(encoding="utf-8")
    return priv, pub, alg


def _create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    st = get_settings()
    sign_key, _, alg = _load_sign_keys()
    exp_min = expires_minutes or st.JWT_EXPIRE_MINUTES

    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=exp_min)).timestamp()),
    }
    return jwt.encode(payload, sign_key, algorithm=alg)


def _decode_token(token: str) -> dict:
    _, verify_key, alg = _load_sign_keys()
    try:
        return jwt.decode(token, verify_key, algorithms=[alg])
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}") from e


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    data = _decode_token(token)
    username = data.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token payload (missing 'sub')")
    return User(username=username, is_authenticated=True)


# ---------- Endpoints ----------
@router.get("/ping")
def ping():
    return {"ok": True, "service": "auth"}


@router.post("/login", response_model=TokenResponse)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()]):
    """
    OAuth2 Password flow:
      Content-Type: application/x-www-form-urlencoded
      username=...&password=...
    """
    username = form.username
    password = form.password

    stored = _USERS.get(username)
    if not stored or not _verify_password(password, stored):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = _create_access_token(username)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=User)
def me(user: Annotated[User, Depends(get_current_user)]):
    return user
