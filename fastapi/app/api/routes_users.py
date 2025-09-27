from __future__ import annotations
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete

from app.db import SessionLocal
from app.models.user import User, Role, UserRole
from app.core.security import hash_password

router = APIRouter(prefix="/users", tags=["users"])

# ====== DB dependency ======
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ====== Schemas ======
class UserOut(BaseModel):
    id: int
    username: str
    email: Optional[EmailStr] = None
    is_active: bool
    is_superuser: bool

    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=120)
    email: Optional[EmailStr] = None
    password: str = Field(min_length=6)
    is_active: bool = True
    is_superuser: bool = False
    roles: Optional[List[str]] = None  # أسماء الأدوار

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    roles: Optional[List[str]] = None  # استبدال كامل للأدوار لو مُرسلة

class PasswordResetIn(BaseModel):
    password: str = Field(min_length=6)

class RoleOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True

# ===== Helpers =====
def _apply_roles(db: Session, user: User, role_names: Optional[List[str]]):
    if role_names is None:
        return
    # اجلب كل الأدوار الموجودة أو أنشئ الناقص
    existing = {r.name: r for r in db.execute(select(Role)).scalars().all()}
    needed = []
    for name in role_names:
        r = existing.get(name)
        if not r:
            r = Role(name=name)
            db.add(r)
            db.flush()
        needed.append(r)
    user.roles = needed  # استبدال كامل
    db.flush()

# ===== Routes =====
@router.get("", response_model=List[UserOut])
def list_users(
    q: Optional[str] = Query(default=None, description="search in username/email"),
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    stmt = select(User)
    if q:
        like = f"%{q}%"
        stmt = stmt.where((User.username.ilike(like)) | (User.email.ilike(like)))
    stmt = stmt.order_by(User.id).offset((page - 1) * page_size).limit(page_size)
    return db.execute(stmt).scalars().all()

@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return user

@router.post("", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    if db.execute(select(User).where(User.username == payload.username)).scalar_one_or_none():
        raise HTTPException(409, "Username already exists")
    if payload.email and db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none():
        raise HTTPException(409, "Email already exists")

    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),  # scrypt
        is_active=payload.is_active,
        is_superuser=payload.is_superuser,
    )
    db.add(user)
    db.flush()
    _apply_roles(db, user, payload.roles)
    db.commit()
    db.refresh(user)
    return user

@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    if payload.email is not None:
        # تحقق من فريدية الإيميل
        if payload.email:
            exists = db.execute(select(User).where(User.email == payload.email, User.id != user_id)).scalar_one_or_none()
            if exists:
                raise HTTPException(409, "Email already exists")
        user.email = payload.email

    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.is_superuser is not None:
        user.is_superuser = payload.is_superuser

    if payload.roles is not None:
        _apply_roles(db, user, payload.roles)

    db.commit()
    db.refresh(user)
    return user

@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        return
    db.delete(user)
    db.commit()

@router.post("/{user_id}/password", status_code=204)
def reset_password(user_id: int, payload: PasswordResetIn, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    user.password_hash = hash_password(payload.password)
    db.commit()

@router.get("/roles/list", response_model=List[RoleOut])
def list_roles(db: Session = Depends(get_db)):
    return db.execute(select(Role)).scalars().all()
