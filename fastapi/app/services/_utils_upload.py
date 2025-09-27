# app/services/_utils_upload.py
from __future__ import annotations
import base64
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional


UPLOADS_ROOT = Path("uploads")

def strip_data_url(b64: str) -> str:
    if "," in b64 and ";base64" in b64[:128]:
        return b64.split(",", 1)[1]
    return b64

def b64_to_bytes(b64: str) -> bytes:
    return base64.b64decode(strip_data_url(b64), validate=False)

def sha256_hex(data: bytes) -> str:
    import hashlib
    return hashlib.sha256(data).hexdigest()

def ym_subdir(root: Path) -> Path:
    now = datetime.now()
    sub = root / f"{now:%Y}" / f"{now:%m}"
    sub.mkdir(parents=True, exist_ok=True)
    return sub

def ensure_ext(ext: Optional[str], default_ext: str) -> str:
    if not ext:
        ext = default_ext
    ext = ext.strip().lower()
    if not ext.startswith("."):
        ext = "." + ext
    return "".join(ch for ch in ext if ch.isalnum() or ch in "._-").replace("..", ".")
