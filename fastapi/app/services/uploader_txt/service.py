# Path from repo root: fastapi\app\services\uploader_txt\service.py
from __future__ import annotations
from pathlib import Path
from typing import Any
from app.services.base import BaseService
from app.services._utils_upload import (
    UPLOADS_ROOT, b64_to_bytes, sha256_hex, ym_subdir, ensure_ext
)

TASKS = ["upload_txt"]

def get_tasks() -> list[str]:
    return TASKS


class Service(BaseService):
    name = "uploader_txt"
    tasks = TASKS

    ROOT = UPLOADS_ROOT / "txt"
    MAX_BYTES = 5 * 1024 * 1024  # 5 MB

    def __init__(self) -> None:
        self.ROOT.mkdir(parents=True, exist_ok=True)

    def upload_txt(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        payload:
          - content_b64: required (may be data URL)
          - filename: optional (used only for extension hint)
        """
        b64 = (payload or {}).get("content_b64")
        if not b64:
            return {"ok": False, "error": "content_b64 is required"}

        ext_hint = payload.get("ext") or (
            Path(str(payload.get("filename", ""))).suffix if payload.get("filename") else None
        )
        ext = ensure_ext(ext_hint, ".txt")

        if ext != ".txt":
            return {"ok": False, "error": f"only .txt allowed, not {ext}"}

        try:
            data = b64_to_bytes(str(b64))
        except Exception as exc:
            return {"ok": False, "error": f"invalid base64: {exc}"}

        size = len(data)
        if size == 0:
            return {"ok": False, "error": "empty file"}
        if size > self.MAX_BYTES:
            return {"ok": False, "error": f"TXT too large (> {self.MAX_BYTES} bytes)"}

        # محاولة بسيطة للتأكد أن المحتوى نص (كل bytes < 128)
        if not all(b < 128 for b in data[:1024]):  # نختبر أول 1KB فقط
            return {"ok": False, "error": "file does not look like plain text"}

        subdir = ym_subdir(self.ROOT)
        sha = sha256_hex(data)
        path = subdir / f"{sha[:16]}{ext}"
        if not path.exists():
            path.write_bytes(data)

        rel_path = str(path.relative_to(UPLOADS_ROOT)).replace("\\", "/")
        return {
            "ok": True,
            "rel_path": rel_path,
            "size": size,
            "sha256": sha,
            "mime": "text/plain",
        }