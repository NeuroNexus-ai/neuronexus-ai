# fastapi/app/api/deps.py
from __future__ import annotations
from sqlalchemy.orm import Session
from fastapi import Depends
from app.db import SessionLocal

def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
