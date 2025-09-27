from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from passlib.hash import bcrypt
from app.api.deps import require_roles
from app.models.user import User, Role, UserRole
from app.db import SessionLocal

router = APIRouter(prefix="/users", tags=["users"])

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

class UserCreate(BaseModel):
    username: str
    email: EmailStr | None = None
    password: str
    roles: list[str] = []

@router.post("", dependencies=[Depends(require_roles("admin"))])
def create_user(body: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(409, "username exists")
    u = User(
        username=body.username,
        email=body.email,
        password_hash=bcrypt.hash(body.password),
        is_active=True
    )
    db.add(u); db.flush()
    for rname in body.roles:
        r = db.query(Role).filter(Role.name == rname).first() or Role(name=rname)
        db.add(r); db.flush()
        db.add(UserRole(user_id=u.id, role_id=r.id))
    db.commit()
    return {"id": u.id, "username": u.username, "roles": body.roles}
