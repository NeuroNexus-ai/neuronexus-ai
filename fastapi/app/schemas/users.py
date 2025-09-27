# Path from repo root: fastapi\app\schemas\users.py
from __future__ import annotations
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ---------- Inbound (requests) ----------
class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=120)
    email: Optional[EmailStr] = None
    password: str = Field(min_length=6, max_length=256)


class UserUpdate(BaseModel):
    # all optional to support partial update
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=6, max_length=256)
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


# ---------- Outbound (responses) ----------
class RoleOut(BaseModel):
    name: str
    description: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)  # pydantic v2


class UserOut(BaseModel):
    id: int
    username: str
    email: Optional[EmailStr] = None
    is_active: bool
    is_superuser: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)  # pydantic v2