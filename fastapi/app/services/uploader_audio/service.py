from __future__ import annotations
from pathlib import Path
from typing import Any, Optional
from app.services.base import BaseService
from app.services._utils_upload import (
    UPLOADS_ROOT, b64_to_bytes, sha256_hex, ym_subdir, ensure_ext
)

TASKS = ["upload_audio"]
def get_tasks() -> list[str]: return TASKS

def is_wav(b: bytes) -> bool:
    return len(b) >= 12 and b[:4] == b"RIFF" and b[8:12] == b"WAVE"

def is_mp3(b: bytes) -> bool:
    return b[:3] == b"ID3" or (len(b) >= 2 and b[0] == 0xFF and (b[1] & 0xE0) == 0xE0)

def is_ogg(b: bytes) -> bool:
    return b[:4] == b"OggS"

ALLOWED_EXTS = {".wav": is_wav, ".mp3": is_mp3, ".ogg": is_ogg}

class Service(BaseService):
    name = "uploader_audio"
    tasks = TASKS

    ROOT = UPLOADS_ROOT / "audio"
    MAX_BYTES = 200 * 1024 * 1024  # 200 MB

    def __init__(self) -> None:
        self.Root = self.ROOT
        self.Root.mkdir(parents=True, exist_ok=True)

    def upload_audio(self, payload: dict[str, Any]) -> dict[str, Any]:
        b64 = (payload or {}).get("content_b64")
        if not b64:
            return {"ok": False, "error": "content_b64 is required"}

        ext_hint: Optional[str] = payload.get("ext")
        if not ext_hint and payload.get("filename"):
            ext_hint = Path(str(payload["filename"])).suffix
        ext = ensure_ext(ext_hint, ".wav")

        if ext not in ALLOWED_EXTS:
            return {"ok": False, "error": f"extension not allowed: {ext}"}

        try:
            data = b64_to_bytes(str(b64))
        except Exception as exc:
            return {"ok": False, "error": f"invalid base64: {exc}"}

        size = len(data)
        if size == 0:
            return {"ok": False, "error": "empty file"}
        if size > self.MAX_BYTES:
            return {"ok": False, "error": f"Audio too large (> {self.MAX_BYTES} bytes)"}

        # Magic check
        if not ALLOWED_EXTS[ext](data):
            return {"ok": False, "error": f"invalid audio content for {ext}"}

        subdir = ym_subdir(self.Root)
        sha = sha256_hex(data)
        path = subdir / f"{sha[:16]}{ext}"
        if not path.exists():
            path.write_bytes(data)

        rel_path = str(path.relative_to(UPLOADS_ROOT)).replace("\\", "/")
        mime = "audio/" + ext.lstrip(".")
        return {"ok": True, "rel_path": rel_path, "size": size, "sha256": sha, "mime": mime}
