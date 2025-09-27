# app/api/routes_auth.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.users import UserCreate
from app.crud.users import get_by_username, create_user
from app.core.security import verify_password, needs_rehash, hash_password

# موديول الـ JWT يجب أن يوفّر: create_access_token, create_refresh_token, decode_token
# (إذا كان عندك اختلاف أسماء الحقول في config مثل JWT_ALGORITHM مقابل JWT_ALG، حدّث app/core/jwt.py ليناسب config.py الحالي)
from app.core.jwt import create_access_token, create_refresh_token, decode_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
def register(payload: UserCreate, db: Session = Depends(get_db)):
    """
    إنشاء مستخدم جديد وتخزين كلمة المرور بـ scrypt.
    """
    if get_by_username(db, payload.username):
        raise HTTPException(status_code=400, detail="Username already exists")
    u = create_user(db, payload.username, payload.password, payload.email)
    return {"id": u.id, "username": u.username, "email": u.email}


@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    OAuth2 Password flow:
      Content-Type: application/x-www-form-urlencoded
      username=<user>&password=<pass>
    يرجّع access/refresh JWT عند نجاح التحقق.
    """
    username = form.username
    password = form.password

    user = get_by_username(db, username)
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # ترحيل كسول: إن كان الهاش قديم (bcrypt) أو تغيّرت معاملات scrypt → أعد الهاش وخزّنه
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
        db.add(user)
        db.commit()

    # اجمع الأدوار إن كانت موجودة في الموديل، وإلا أرسل قائمة فارغة
    try:
        roles = [ur.role.name for ur in getattr(user, "roles", [])]
    except Exception:
        roles = []

    return {
        "access_token": create_access_token(user.username, roles),
        "refresh_token": create_refresh_token(user.username),
        "token_type": "bearer",
    }


@router.post("/refresh")
def refresh(refresh_token: str):
    """
    تجديد access token باستخدام refresh token صالح.
    """
    payload = decode_token(refresh_token)
    if payload.get("scope") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    # بإمكانك إعادة جلب الأدوار من DB لضبط أدقّ؛ هنا نعيدها فارغة أو يمكنك تعديلها لاحقًا.
    return {"access_token": create_access_token(subject, roles=[]), "token_type": "bearer"}
