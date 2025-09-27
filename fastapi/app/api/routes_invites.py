from __future__ import annotations
import os, secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from passlib.hash import bcrypt
from app.api.deps import require_roles
from app.models.user import User, Invite
from app.db import SessionLocal

router = APIRouter(prefix="/auth", tags=["auth"])
INVITES_ON = os.getenv("APP_ENABLE_INVITES", "false").lower() == "true"

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

class InviteCreate(BaseModel):
    email: EmailStr | None = None
    ttl_hours: int = 48

@router.post("/invites", dependencies=[Depends(require_roles("admin"))])
def create_invite(body: InviteCreate, db: Session = Depends(get_db)):
    if not INVITES_ON: raise HTTPException(403, "Invites disabled")
    code = secrets.token_urlsafe(24)
    inv = Invite(
        code=code,
        email=body.email,
        expires_at=datetime.utcnow() + timedelta(hours=body.ttl_hours),
    )
    db.add(inv); db.commit()
    return {"code": code, "expires_at": inv.expires_at}

class InviteUse(BaseModel):
    code: str
    username: str
    password: str
    email: EmailStr | None = None

@router.post("/invite")
def use_invite(body: InviteUse, db: Session = Depends(get_db)):
    if not INVITES_ON: raise HTTPException(403, "Invites disabled")
    inv = db.query(Invite).filter(Invite.code == body.code).first()
    if not inv or (inv.expires_at and inv.expires_at < datetime.utcnow()) or inv.used_by_user_id:
        raise HTTPException(400, "Invalid or expired invite")
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(409, "username exists")
    u = User(username=body.username, email=body.email,
             password_hash=bcrypt.hash(body.password), is_active=True)
    db.add(u); db.flush()
    inv.used_by_user_id = u.id
    db.commit()
    return {"ok": True, "id": u.id}
