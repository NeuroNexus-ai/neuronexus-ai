# Path from repo root: fastapi\app\api\deps.py

from __future__ import annotations
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
import jwt, os
from typing import Annotated, List

JWT_SECRET = os.getenv("APP_JWT_SECRET", "changeme")
security = HTTPBearer()

def current_user_roles(token=Depends(security)) -> List[str]:
    try:
        payload = jwt.decode(token.credentials, JWT_SECRET, algorithms=["HS256"])
        return payload.get("roles", [])
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

def require_roles(*needed: str):
    def wrapper(roles: List[str] = Depends(current_user_roles)):
        if any(r for r in roles if r in needed) or "admin" in roles:
            return True
        raise HTTPException(status_code=403, detail="Forbidden")
    return wrapper