# Path from repo root: fastapi\app\services\uploader_video\service.py
from __future__ import annotations
from typing import Any, Optional
from pathlib import Path

from app.services.base import BaseService
from app.services._utils_upload import (
    UPLOADS_ROOT, b64_to_bytes, sha256_hex, ym_subdir, ensure_ext
)

"""
Supported (by extension + magic check):
- .mp4  -> ISO BMFF ('ftyp' within first 64 bytes) + major brand like isom/mp41/mp42/avc1
- .mov  -> ISO BMFF with QuickTime brand 'qt  ' or 'ftypqt  '
- .mkv  -> EBML header 1A 45 DF A3 (Matroska); DocType='matroska'
- .webm -> EBML header; DocType='webm'
- .avi  -> RIFF....'AVI ' chunk

Max size: 1 GB
Path: uploads/video/YYYY/MM/<sha16>.<ext>
"""

TASKS = ["upload_video"]
def get_tasks() -> list[str]:
    return TASKS


class Service(BaseService):
    name = "uploader_video"
    tasks = TASKS

    ROOT = UPLOADS_ROOT / "video"
    MAX_BYTES = 1 * 1024 * 1024 * 1024  # 1 GB

    MIME_MAP = {
        ".mp4":  "video/mp4",
        ".mov":  "video/quicktime",
        ".mkv":  "video/x-matroska",
        ".webm": "video/webm",
        ".avi":  "video/x-msvideo",
    }

    ALLOWED_EXTS = set(MIME_MAP.keys())

    def __init__(self) -> None:
        self.ROOT.mkdir(parents=True, exist_ok=True)

    # ---------- magic helpers ----------

    @staticmethod
    def _has_ftyp(data: bytes) -> bool:
        # ISO BMFF files contain 'ftyp' box near start (within first ~32-64 bytes)
        search_window = data[:128]
        return b"ftyp" in search_window

    @staticmethod
    def _mp4_brand_ok(data: bytes) -> bool:
        # MP4 common brands: isom, mp41, mp42, avc1 (best-effort)
        head = data[:128]
        return any(b in head for b in (b"isom", b"mp41", b"mp42", b"avc1"))

    @staticmethod
    def _mov_brand_ok(data: bytes) -> bool:
        # QuickTime brand often 'qt  ' or 'ftypqt  '
        head = data[:128]
        return b"ftypqt" in head or b"qt  " in head

    @staticmethod
    def _is_ebml(data: bytes) -> bool:
        # EBML header: 1A 45 DF A3
        return len(data) >= 4 and data[:4] == bytes.fromhex("1A45DFA3")

    @staticmethod
    def _ebml_doctype(data: bytes) -> Optional[str]:
        # Lightweight docType sniff: search small window for 'webm' or 'matroska'
        head = data[:4096]
        if b"webm" in head:
            return "webm"
        if b"matroska" in head:
            return "matroska"
        return None

    @staticmethod
    def _is_avi(data: bytes) -> bool:
        # RIFF....AVI
        return len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"AVI "

    # ---------- main task ----------

    def upload_video(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        payload:
          - content_b64: required (may be data URL)
          - ext: optional ('.mp4' | '.mov' | '.mkv' | '.webm' | '.avi')
          - filename: optional (used only as extension hint)
        """
        b64 = (payload or {}).get("content_b64")
        if not b64:
            return {"ok": False, "error": "content_b64 is required"}

        ext_hint: Optional[str] = payload.get("ext")
        if not ext_hint and payload.get("filename"):
            ext_hint = Path(str(payload["filename"])).suffix
        ext = ensure_ext(ext_hint, ".mp4")

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
            return {"ok": False, "error": f"Video too large (> {self.MAX_BYTES} bytes)"}

        # Magic checks per extension
        ok = False
        if ext in (".mp4", ".mov"):
            ok = self._has_ftyp(data) and (
                self._mp4_brand_ok(data) if ext == ".mp4" else self._mov_brand_ok(data)
            )
        elif ext in (".mkv", ".webm"):
            if self._is_ebml(data):
                dt = self._ebml_doctype(data)
                ok = (ext == ".mkv" and dt == "matroska") or (ext == ".webm" and dt == "webm")
        elif ext == ".avi":
            ok = self._is_avi(data)

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