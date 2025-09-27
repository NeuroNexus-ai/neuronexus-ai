# Path from repo root: fastapi\app\core\security.py
from __future__ import annotations
import os, base64, hashlib
from typing import Tuple

SCRYPT_N        = int(os.getenv("SCRYPT_N", str(2**14)))
SCRYPT_R        = int(os.getenv("SCRYPT_R", "8"))
SCRYPT_P        = int(os.getenv("SCRYPT_P", "1"))
SCRYPT_DK_LEN   = int(os.getenv("SCRYPT_DKLEN", "64"))
SCRYPT_SALT_LEN = int(os.getenv("SCRYPT_SALT_LEN", "16"))

def _b64e(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")

def _b64d(s: str) -> bytes:
    return base64.b64decode(s.encode("ascii"))

def _derive(password: str, salt: bytes, n: int, r: int, p: int, dklen: int) -> bytes:
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=dklen)

def hash_password(password: str) -> str:
    salt = os.urandom(SCRYPT_SALT_LEN)
    key  = _derive(password, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P, SCRYPT_DK_LEN)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${SCRYPT_DK_LEN}${_b64e(salt)}${_b64e(key)}"

def _parse(encoded: str) -> Tuple[int, int, int, int, bytes, bytes]:
    # format: scrypt$N$r$p$dklen$salt_b64$key_b64
    scheme, n, r, p, dklen, salt_b64, key_b64 = encoded.split("$", 6)
    if scheme != "scrypt":
        raise ValueError("Unsupported password scheme")
    return int(n), int(r), int(p), int(dklen), _b64d(salt_b64), _b64d(key_b64)

def verify_password(password: str, encoded: str) -> bool:
    n, r, p, dklen, salt, key = _parse(encoded)
    test = _derive(password, salt, n, r, p, dklen)
    # constant-time compare
    if len(test) != len(key):
        return False
    result = 0
    for a, b in zip(test, key):
        result |= a ^ b
    return result == 0
