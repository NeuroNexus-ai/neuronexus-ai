# Path from repo root: fastapi\tools\reset_admin.py
"""
Reset or create the admin user (scrypt password).
Usage:
    py fastapi/tools/reset_admin.py --create-if-missing
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path
from typing import Optional

# --- Make sure imports work ---
HERE = Path(__file__).resolve()
FASTAPI_DIR = HERE.parents[1]
if str(FASTAPI_DIR) not in sys.path:
    sys.path.insert(0, str(FASTAPI_DIR))

# --- Project imports ---
from sqlalchemy import or_
from app.db import SessionLocal  # type: ignore
from app.models.user import User  # type: ignore
from app.core.security import hash_password  # type: ignore


def _env(key: str, default: Optional[str] = None) -> Optional[str]:
    val = os.getenv(key)
    if val is None:
        return default
    val = val.strip()
    return val or default


def _prompt_nonempty(prompt: str, hidden: bool = False) -> str:
    while True:
        try:
            v = getpass.getpass(prompt) if hidden else input(prompt)
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            sys.exit(1)
        v = (v or "").strip()
        if v:
            return v
        print("⚠️  Required field. Please try again.")


def _prompt_password() -> str:
    while True:
        p1 = getpass.getpass("New password: ")
        p2 = getpass.getpass("Confirm password: ")
        if p1 != p2:
            print("⚠️  Passwords do not match. Try again.")
            continue
        if len(p1) < 6:
            print("⚠️  Too short (min 6 chars). Try again.")
            continue
        return p1


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Reset or create admin user.")
    p.add_argument("--username", "-u", type=str, help="Username (default: admin)")
    p.add_argument("--email", "-e", type=str, help="Email (used on create)")
    p.add_argument("--password", "-p", type=str, help="Password (DANGEROUS on shared shells)")
    p.add_argument("--from-env", action="store_true", help="Read from env: ADMIN_USER/ADMIN_PASS/ADMIN_EMAIL")
    p.add_argument("--create-if-missing", action="store_true", help="Create the user if not found")
    p.add_argument("--make-superuser", action="store_true", default=True, help="Ensure is_superuser=True")
    p.add_argument("--no-make-superuser", dest="make_superuser", action="store_false")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    # Resolve inputs
    username = args.username or _env("ADMIN_USER", "admin")
    email = args.email or _env("ADMIN_EMAIL")
    password = args.password

    if args.from_env:
        username = _env("ADMIN_USER", username)
        password = _env("ADMIN_PASS", password)
        email = _env("ADMIN_EMAIL", email)

    if not username:
        username = _prompt_nonempty("Username: ")

    if not password:
        password = _prompt_password()

    # Hash with project's scrypt
    try:
        pwd_hash = hash_password(password)
    except Exception as ex:
        print(f"❌ Failed to hash password via scrypt: {ex}")
        return 2

    db = SessionLocal()
    try:
        conds = [User.username == username]
        if email:
            conds.append(User.email == email)
        user = db.query(User).filter(or_(*conds)).first()

        if user is None:
            if not args.create_if_missing:
                print(f"❌ User '{username}' not found. Use --create-if-missing to create.")
                return 1
            user = User(
                username=username,
                email=email,
                password_hash=pwd_hash,
                is_active=True,
                is_superuser=bool(args.make_superuser),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"✅ Created user '{username}' (id={user.id})")
        else:
            user.password_hash = pwd_hash
            if args.make_superuser:
                user.is_superuser = True
            user.is_active = True
            if email and not user.email:
                user.email = email
            db.commit()
            print(f"✅ Updated password for '{username}' (id={user.id})")

        print("💡 Test login now via:")
        print(
            'curl.exe -X POST "http://127.0.0.1:8000/auth/login" '
            '-H "Content-Type: application/x-www-form-urlencoded" '
            '--data-urlencode "grant_type=password" '
            f'--data-urlencode "username={username}" '
            f'--data-urlencode "password=***"'
        )
        return 0
    except Exception as ex:
        db.rollback()
        print(f"❌ Database error: {ex}")
        return 3
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())