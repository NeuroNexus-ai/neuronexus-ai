# Path from repo root: fastapi\app\api\routes_auth.py

from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.security import create_access_token, create_refresh_token
from app.models.user import User, RefreshToken
from app.db import SessionLocal
from passlib.hash import bcrypt
from datetime import datetime
from typing import Optional, List

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginIn(BaseModel):
    username: str
    password: str

class TokensOut(BaseModel):
    access_token: str
    refresh_token: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/login", response_model=TokensOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    u: Optional[User] = db.query(User).filter(User.username == body.username).first()
    if not u or not u.is_active or not bcrypt.verify(body.password, u.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    roles = ["admin"] if u.is_superuser else [
        r.role.name for r in u.roles
    ]
    access = create_access_token(sub=str(u.id), roles=roles)
    refresh, exp = create_refresh_token(sub=str(u.id))

    # persist refresh (hashed)
    rt = RefreshToken(user_id=u.id,
                      token_hash=bcrypt.hash(refresh),
                      expires_at=exp)
    db.add(rt); db.commit()
    return {"access_token": access, "refresh_token": refresh}

@router.get("/me")
def me(roles: List[str] = Depends(lambda: []), db: Session = Depends(get_db)):
    return {"ok": True, "roles": roles}

class RefreshIn(BaseModel):
    refresh_token: str

@router.post("/refresh", response_model=TokensOut)
def refresh(body: RefreshIn, db: Session = Depends(get_db)):
    new_access = create_access_token(sub="unknown", roles=[])
    new_refresh, _ = create_refresh_token(sub="unknown")
    return {"access_token": new_access, "refresh_token": new_refresh}