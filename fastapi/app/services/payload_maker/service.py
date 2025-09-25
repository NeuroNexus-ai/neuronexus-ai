from __future__ import annotations
from pathlib import Path
from typing import Any, Optional
import base64, mimetypes

from app.services.base import BaseService
from app.services._utils_upload import sha256_hex  # لديك مسبقًا

TASKS = ["make_b64_payload"]
def get_tasks() -> list[str]: return TASKS

class Service(BaseService):
    name = "payload_maker"
    tasks = TASKS

    def make_b64_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        payload:
          - path: مسار مطلق أو نسبي (اختياري)
          - rel_path: مسار نسبي داخل uploads/ (اختياري)
          - mime: اختياري (إن لم يُستنتج من الامتداد)
          - add_prefix: bool (افتراضي True) -> يضيف "data:<mime>;base64,"
        واحد من path أو rel_path مطلوب.
        """
        add_prefix = bool(payload.get("add_prefix", True))

        # حدد المسار
        file_path: Optional[Path] = None
        if payload.get("rel_path"):
            p = Path("uploads") / str(payload["rel_path"])
            file_path = p.resolve()
        elif payload.get("path"):
            file_path = Path(str(payload["path"])).expanduser().resolve()
        else:
            return {"ok": False, "error": "provide path or rel_path"}

        if not file_path.is_file():
            return {"ok": False, "error": f"file not found: {file_path}"}

        data = file_path.read_bytes()
        if len(data) == 0:
            return {"ok": False, "error": "empty file"}

        # استنتاج الـ MIME
        mime = payload.get("mime")
        if not mime:
            guessed, _ = mimetypes.guess_type(str(file_path))
            mime = guessed or "application/octet-stream"

        b64 = base64.b64encode(data).decode("utf-8")
        content_b64 = (f"data:{mime};base64,{b64}") if add_prefix else b64

        return {
            "ok": True,
            "content_b64": content_b64,
            "size": len(data),
            "sha256": sha256_hex(data),
            "mime": mime,
            "filename": file_path.name,
        }
