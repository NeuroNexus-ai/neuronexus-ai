# app/core/security.py
from __future__ import annotations

import base64
import hashlib
import os
from typing import Optional, Tuple

# Scrypt settings (can be configured via environment variables)
SCRYPT_N = int(os.getenv("SCRYPT_N", 2**14))  # Cost factor (preferably a power of 2)
SCRYPT_R = int(os.getenv("SCRYPT_R", 8))
SCRYPT_P = int(os.getenv("SCRYPT_P", 1))
SCRYPT_DK_LEN = int(os.getenv("SCRYPT_DKLEN", 64))
SCRYPT_SALT_LEN = int(os.getenv("SCRYPT_SALT_LEN", 16))

# Storage format: scrypt$<N>$<r>$<p>$<dklen>$<salt_b64>$<hash_b64>
# Example: scrypt$16384$8$1$64$<salt>$<key>

def _b64e(b: bytes) -> str:
    """Base64-encode bytes and return as ASCII string."""
    return base64.b64encode(b).decode("ascii")

def _b64d(s: str) -> bytes:
    """Decode a base64 ASCII string into bytes."""
    return base64.b64decode(s.encode("ascii"))

def _derive(password: str, salt: bytes, n: int, r: int, p: int, dklen: int) -> bytes:
    """Derive a cryptographic key using the scrypt algorithm."""
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=dklen)

def hash_password(password: str) -> str:
    """
    Hash a password using scrypt with environment-configured parameters.

    Args:
        password (str): Plain-text password.

    Returns:
        str: The hashed password in scrypt$<N>$<r>$<p>$<dklen>$<salt>$<hash> format.
    """
    salt = os.urandom(SCRYPT_SALT_LEN)
    key = _derive(password, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P, SCRYPT_DK_LEN)
    return (
        f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${SCRYPT_DK_LEN}" 
        f"${_b64e(salt)}${'$'}{_b64e(key)}"
    )

def _parse_scrypt(stored: str) -> Tuple[int, int, int, int, bytes, bytes]:
    """
    Parse a stored scrypt password string into components.

    Args:
        stored (str): Stored password string.

    Returns:
        Tuple: n, r, p, dklen, salt, key
    """
    parts = stored.split("$")
    if len(parts) != 7 or parts[0] != "scrypt":
        raise ValueError("not scrypt format")
    n = int(parts[1])
    r = int(parts[2])
    p = int(parts[3])
    dklen = int(parts[4])
    salt = _b64d(parts[5])
    key = _b64d(parts[6])
    return n, r, p, dklen, salt, key

def verify_password(password: str, stored: str) -> bool:
    """
    Verify a password against a stored hash, supporting scrypt and optionally bcrypt.

    Args:
        password (str): Plain-text password.
        stored (str): Stored hashed password.

    Returns:
        bool: True if the password matches the hash, False otherwise.
    """
    if stored.startswith("scrypt$"):
        n, r, p, dklen, salt, key = _parse_scrypt(stored)
        new_key = _derive(password, salt, n, r, p, dklen)
        return hashlib.compare_digest(key, new_key)

    if stored.startswith("$2a$") or stored.startswith("$2b$") or \
       stored.startswith("$2y$") or stored.startswith("bcrypt$"):
        try:
            from passlib.hash import bcrypt
            raw = stored.split("$", 1)[1] if stored.startswith("bcrypt$") else stored
            return bcrypt.verify(password, raw)
        except Exception:
            return False

    return False

def needs_rehash(stored: str) -> bool:
    """
    Check whether a stored password hash needs to be rehashed (e.g., settings changed).

    Args:
        stored (str): Stored hashed password.

    Returns:
        bool: True if the hash needs rehashing, False otherwise.
    """
    if not stored.startswith("scrypt$"):
        return True

    try:
        n, r, p, dklen, _salt, _key = _parse_scrypt(stored)
        return any([
            n != SCRYPT_N,
            r != SCRYPT_R,
            p != SCRYPT_P,
            dklen != SCRYPT_DK_LEN,
        ])
    except Exception:
        return True
