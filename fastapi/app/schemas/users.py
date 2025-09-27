# Path from repo root: fastapi\app\schemas\users.py
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, EmailStr, Field

# Shared properties
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: Optional[EmailStr] = None
    is_active: bool = True
    is_superuser: bool = False

# Create
class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=128)

# Update (partial)
class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=64)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=6, max_length=128)

# DB → API (out)
class UserOut(UserBase):
    id: int

    class Config:
        from_attributes = True  # SQLAlchemy compatibility
