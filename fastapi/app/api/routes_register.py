from __future__ import annotations
import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from passlib.hash import bcrypt
from app.models.user import User
from app.db import SessionLocal

router = APIRouter(prefix="/auth", tags=["auth"])
SELF_SIGNUP = os.getenv("APP_ENABLE_SELF_SIGNUP", "false").lower() == "true"

class RegisterIn(BaseModel):
    username: str
    email: EmailStr | None = None
    password: str

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

@router.post("/register")
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if not SELF_SIGNUP:
        raise HTTPException(403, "Self-sign-up disabled")
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(409, "username exists")
    u = User(username=body.username, email=body.email,
             password_hash=bcrypt.hash(body.password), is_active=True)
    db.add(u); db.commit()
    return {"ok": True, "id": u.id}
