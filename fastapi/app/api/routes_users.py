# Path from repo root: fastapi\app\api\routes_users.py
from __future__ import annotations
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.crud import users as crud_users

router = APIRouter(prefix="/users", tags=["users"])

# --- DB dependency ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Auth placeholder (to be replaced with real JWT) ---
def require_superuser() -> None:
    # TODO: Replace with JWT-based check in next step.
    # For now, allow everything for local testing:
    return

@router.get("/", response_model=List[UserOut])
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _=Depends(require_superuser),
):
    return list(crud_users.list_users(db, skip=skip, limit=limit))

@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_superuser),
):
    u = crud_users.get_by_id(db, user_id)
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return u

@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    _=Depends(require_superuser),
):
    try:
        return crud_users.create_user(db, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_superuser),
):
    u = crud_users.get_by_id(db, user_id)
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    try:
        return crud_users.update_user(db, u, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_superuser),
):
    u = crud_users.get_by_id(db, user_id)
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    crud_users.delete_user(db, u)
    return