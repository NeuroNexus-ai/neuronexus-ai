# Path from repo root: fastapi\app\schemas\auth.py
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, EmailStr, constr


class LoginIn(BaseModel):
    username: str  # can be username or email
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    is_active: bool
    is_superuser: bool
    roles: List[str] = []


class RefreshIn(BaseModel):
    refresh_token: str
