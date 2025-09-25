from __future__ import annotations
from typing import Any, Optional
from pathlib import Path

from app.services.base import BaseService
from app.services._utils_upload import (
    UPLOADS_ROOT, b64_to_bytes, sha256_hex, ym_subdir, ensure_ext
)

"""
Supported images (by extension + magic check):
- .jpg/.jpeg -> FF D8 FF
- .png       -> 89 50 4E 47 0D 0A 1A 0A
- .gif       -> "GIF87a" or "GIF89a"
- .webp      -> RIFF....WEBP
- .heic      -> ISO BMFF 'ftyp' + 'heic'/'heif' brand  (اختياري، مفعّل هنا)

(نستثني SVG افتراضيًا لأسباب أمان، لأنه نص XML ممكن يحتوي سكربتات. ممكن تفعيله لاحقًا مع تعقيم.)
Max size: 25 MB
Path: uploads/images/YYYY/MM/<sha16>.<ext>
"""

TASKS = ["upload_image"]
def get_tasks() -> list[str]:
    return TASKS


class Service(BaseService):
    name = "uploader_image"
    tasks = TASKS

    ROOT = UPLOADS_ROOT / "images"
    MAX_BYTES = 25 * 1024 * 1024  # 25 MB

    MIME_MAP = {
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png":  "image/png",
        ".gif":  "image/gif",
        ".webp": "image/webp",
        ".heic": "image/heic",  # بعض المتصفحات لا تتعرف عليه مباشرة
    }
    ALLOWED_EXTS = set(MIME_MAP.keys())

    def __init__(self) -> None:
        self.ROOT.mkdir(parents=True, exist_ok=True)

    # ---------- magic helpers ----------

    @staticmethod
    def _is_jpeg(b: bytes) -> bool:
        return len(b) >= 3 and b[:3] == b"\xFF\xD8\xFF"

    @staticmethod
    def _is_png(b: bytes) -> bool:
        return b[:8] == bytes.fromhex("89504E470D0A1A0A")

    @staticmethod
    def _is_gif(b: bytes) -> bool:
        return b[:6] in (b"GIF87a", b"GIF89a")

    @staticmethod
    def _is_webp(b: bytes) -> bool:
        return len(b) >= 12 and b[:4] == b"RIFF" and b[8:12] == b"WEBP"

    @staticmethod
    def _has_ftyp(b: bytes) -> bool:
        return b"ftyp" in b[:128]

    @staticmethod
    def _heic_brand_ok(b: bytes) -> bool:
        head = b[:256]
        # أشهر العلامات: 'heic', 'heif', 'hevc', 'mif1'
        return any(tag in head for tag in (b"heic", b"heif", b"hevc", b"mif1"))

    # ---------- main task ----------

    def upload_image(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        payload:
          - content_b64: required (may be data URL)
          - ext: optional ('.jpg'|'.jpeg'|'.png'|'.gif'|'.webp'|'.heic')
          - filename: optional (used as extension hint)
        """
        b64 = (payload or {}).get("content_b64")
        if not b64:
            return {"ok": False, "error": "content_b64 is required"}

        ext_hint: Optional[str] = payload.get("ext")
        if not ext_hint and payload.get("filename"):
            ext_hint = Path(str(payload["filename"])).suffix
        ext = ensure_ext(ext_hint, ".jpg")

        if ext not in self.ALLOWED_EXTS:
            return {"ok": False, "error": f"extension not allowed: {ext}"}

        try:
            data = b64_to_bytes(str(b64))
        except Exception as exc:
            return {"ok": False, "error": f"invalid base64: {exc}"}

        size = len(data)
        if size == 0:
            return {"ok": False, "error": "empty file"}
        if size > self.MAX_BYTES:
            return {"ok": False, "error": f"Image too large (> {self.MAX_BYTES} bytes)"}

        # Magic checks per extension
        ok = False
        if ext in (".jpg", ".jpeg"): ok = self._is_jpeg(data)
        elif ext == ".png":          ok = self._is_png(data)
        elif ext == ".gif":          ok = self._is_gif(data)
        elif ext == ".webp":         ok = self._is_webp(data)
        elif ext == ".heic":         ok = self._has_ftyp(data) and self._heic_brand_ok(data)

        if not ok:
            return {"ok": False, "error": f"invalid or unsupported {ext} content"}

        subdir = ym_subdir(self.ROOT)
        sha = sha256_hex(data)
        path = subdir / f"{sha[:16]}{ext}"
        if not path.exists():
            path.write_bytes(data)

        rel_path = str(path.relative_to(UPLOADS_ROOT)).replace("\\", "/")
        mime = self.MIME_MAP[ext]
        return {"ok": True, "rel_path": rel_path, "size": size, "sha256": sha, "mime": mime}
