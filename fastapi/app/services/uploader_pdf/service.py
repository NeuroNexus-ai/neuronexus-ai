# Path from repo root: fastapi\app\services\uploader_pdf\service.py
from __future__ import annotations
from pathlib import Path
from typing import Any
from app.services.base import BaseService
from app.services._utils_upload import (
    UPLOADS_ROOT, b64_to_bytes, sha256_hex, ym_subdir
)

TASKS = ["upload_pdf"]
def get_tasks() -> list[str]: return TASKS

class Service(BaseService):
    name = "uploader_pdf"
    tasks = TASKS

    ROOT = UPLOADS_ROOT / "pdf"
    MAX_BYTES = 50 * 1024 * 1024  # 50 MB

    def __init__(self) -> None:
        self.Root = self.ROOT
        self.Root.mkdir(parents=True, exist_ok=True)

    def upload_pdf(self, payload: dict[str, Any]) -> dict[str, Any]:
        b64 = (payload or {}).get("content_b64")
        if not b64:
            return {"ok": False, "error": "content_b64 is required"}
        try:
            data = b64_to_bytes(str(b64))
        except Exception as exc:
            return {"ok": False, "error": f"invalid base64: {exc}"}

        size = len(data)
        if size == 0:
            return {"ok": False, "error": "empty file"}
        if size > self.MAX_BYTES:
            return {"ok": False, "error": f"PDF too large (> {self.MAX_BYTES} bytes)"}

        # Magic bytes: %PDF
        if not (size >= 4 and data[:4] == b"%PDF"):
            return {"ok": False, "error": "not a valid PDF (missing %PDF header)"}

        subdir = ym_subdir(self.Root)
        sha = sha256_hex(data)
        path = subdir / f"{sha[:16]}.pdf"
        if not path.exists():
            path.write_bytes(data)

        rel_path = str(path.relative_to(UPLOADS_ROOT)).replace("\\", "/")
        return {"ok": True, "rel_path": rel_path, "size": size, "sha256": sha, "mime": "application/pdf"}