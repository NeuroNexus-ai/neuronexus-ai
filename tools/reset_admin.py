#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reset or create the admin user (scrypt password).
Usage (interactive):
    py fastapi/tools/reset_admin.py

Non-interactive (from env):
    setx ADMIN_USER admin
    setx ADMIN_PASS secret123
    setx ADMIN_EMAIL admin@example.com
    py fastapi/tools/reset_admin.py --from-env --create-if-missing

Non-interactive (args):
    py fastapi/tools/reset_admin.py --username admin --password secret123 --email admin@example.com --create-if-missing
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from typing import Optional

# --- Make sure "app/" is importable when executed from project root ---
from pathlib import Path

HERE = Path(__file__).resolve()
FASTAPI_DIR = HERE.parents[1]              # .../fastapi
PROJECT_ROOT = FASTAPI_DIR.parent          # .../neuronexus-ai
if str(FASTAPI_DIR) not in sys.path:
    sys.path.insert(0, str(FASTAPI_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# --- Project imports (sync SQLAlchemy session + User model + scrypt hash) ---
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
    p.add_argument("--username", "-u", type=str, help="Username to reset/create (default: admin)")
    p.add_argument("--email", "-e", type=str, help="Email (used on create)")
    p.add_argument("--password", "-p", type=str, help="Password (DANGEROUS on shared shells)")
    p.add_argument("--from-env", action="store_true", help="Read credentials from env (ADMIN_USER/ADMIN_PASS/ADMIN_EMAIL)")
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
        # Take everything from env (if available)
        username = _env("ADMIN_USER", username)
        password = _env("ADMIN_PASS", password)
        email = _env("ADMIN_EMAIL", email)

    if not username:
        username = _prompt_nonempty("Username: ")

    # If not passing password via args/env, ask interactively
    if not password:
        password = _prompt_password()

    # Hash password with project's scrypt function
    try:
        pwd_hash = hash_password(password)
    except Exception as ex:
        print(f"❌ Failed to hash password via scrypt: {ex}")
        return 2

    db = SessionLocal()
    try:
        user: Optional[User] = (
            db.query(User)
            .filter((User.username == username) | ((email is not None) & (User.email == email)))
            .first()
        )

        if user is None:
            if not args.create_if_missing:
                print(f"❌ User '{username}' not found. Use --create-if-missing to create.")
                return 1
            # Create new user
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
            # Update existing user
            user.password_hash = pwd_hash
            if args.make_superuser:
                user.is_superuser = True
            user.is_active = True
            if email and not user.email:
                user.email = email
            db.commit()
            print(f"✅ Updated password for '{username}' (id={user.id})")

        print("💡 You can test login now via:")
        print("    curl.exe -X POST \"http://127.0.0.1:8000/auth/login\" "
              "-H \"Content-Type: application/x-www-form-urlencoded\" "
              f"--data-urlencode \"grant_type=password\" --data-urlencode \"username={username}\" --data-urlencode \"password=***\"")

        return 0
    except Exception as ex:
        db.rollback()
        print(f"❌ Database error: {ex}")
        return 3
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
