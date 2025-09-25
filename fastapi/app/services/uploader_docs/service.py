from __future__ import annotations
from typing import Any, Optional
from pathlib import Path
from zipfile import ZipFile, BadZipFile

from app.services.base import BaseService
from app.services._utils_upload import (
    UPLOADS_ROOT, b64_to_bytes, sha256_hex, ym_subdir, ensure_ext
)

"""
Supported types (by extension + magic check):

- .docx  -> ZIP with 'word/document.xml'
- .xlsx  -> ZIP with 'xl/workbook.xml'
- .pptx  -> ZIP with 'ppt/presentation.xml'
- .odt   -> ZIP with 'mimetype' = 'application/vnd.oasis.opendocument.text'
- .ods   -> ZIP with 'mimetype' = 'application/vnd.oasis.opendocument.spreadsheet'
- .odp   -> ZIP with 'mimetype' = 'application/vnd.oasis.opendocument.presentation'
- .rtf   -> bytes start with '{\\rtf'
- .doc   -> OLE header D0 CF 11 E0 A1 B1 1A E1  (best-effort quick check)

Max size: 50 MB
Saved under: uploads/docs/YYYY/MM/<sha16>.<ext>
"""

TASKS = ["upload_doc"]
def get_tasks() -> list[str]:
    return TASKS


class Service(BaseService):
    name = "uploader_docs"
    tasks = TASKS

    ROOT = UPLOADS_ROOT / "docs"
    MAX_BYTES = 50 * 1024 * 1024  # 50 MB

    MIME_MAP = {
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".odt":  "application/vnd.oasis.opendocument.text",
        ".ods":  "application/vnd.oasis.opendocument.spreadsheet",
        ".odp":  "application/vnd.oasis.opendocument.presentation",
        ".rtf":  "application/rtf",
        ".doc":  "application/msword",
    }

    ALLOWED_EXTS = set(MIME_MAP.keys())

    def __init__(self) -> None:
        self.ROOT.mkdir(parents=True, exist_ok=True)

    # ---------- magic check helpers ----------

    @staticmethod
    def _is_rtf(data: bytes) -> bool:
        # RTF usually starts with "{\rtf"
        return data[:5] == b"{\\rtf"

    @staticmethod
    def _is_ole_doc(data: bytes) -> bool:
        # Legacy .doc uses OLE Compound File header
        return len(data) >= 8 and data[:8] == bytes.fromhex("D0CF11E0A1B11AE1")

    @staticmethod
    def _zip_has_member(data: bytes, member: str) -> bool:
        try:
            with ZipFile(Path("|mem|"), "r") as _:
                pass  # placeholder (ZipFile doesn't accept raw bytes directly)
        except Exception:
            pass
        # open from bytes safely
        try:
            from io import BytesIO
            with ZipFile(BytesIO(data)) as zf:
                try:
                    zf.getinfo(member)
                    return True
                except KeyError:
                    return False
        except BadZipFile:
            return False
        except Exception:
            return False

    def _is_docx(self, data: bytes) -> bool:
        return self._zip_has_member(data, "word/document.xml")

    def _is_xlsx(self, data: bytes) -> bool:
        return self._zip_has_member(data, "xl/workbook.xml")

    def _is_pptx(self, data: bytes) -> bool:
        return self._zip_has_member(data, "ppt/presentation.xml")

    def _odf_mimetype_is(self, data: bytes, expected: str) -> bool:
        # ODF packages store a 'mimetype' file at root (stored, not compressed)
        try:
            from io import BytesIO
            with ZipFile(BytesIO(data)) as zf:
                try:
                    with zf.open("mimetype", "r") as f:
                        mt = f.read(200).decode("utf-8", errors="ignore").strip()
                        return mt == expected
                except KeyError:
                    return False
        except BadZipFile:
            return False
        except Exception:
            return False

    def _is_odt(self, data: bytes) -> bool:
        return self._odf_mimetype_is(data, "application/vnd.oasis.opendocument.text")

    def _is_ods(self, data: bytes) -> bool:
        return self._odf_mimetype_is(data, "application/vnd.oasis.opendocument.spreadsheet")

    def _is_odp(self, data: bytes) -> bool:
        return self._odf_mimetype_is(data, "application/vnd.oasis.opendocument.presentation")

    # ---------- main task ----------

    def upload_doc(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        payload:
          - content_b64: required (may include data URL prefix)
          - ext: optional ('.docx' | '.xlsx' | '.pptx' | '.odt' | '.ods' | '.odp' | '.rtf' | '.doc')
          - filename: optional (used only as extension hint)
        """
        b64 = (payload or {}).get("content_b64")
        if not b64:
            return {"ok": False, "error": "content_b64 is required"}

        ext_hint: Optional[str] = payload.get("ext")
        if not ext_hint and payload.get("filename"):
            ext_hint = Path(str(payload["filename"])).suffix
        ext = ensure_ext(ext_hint, ".docx")

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
            return {"ok": False, "error": f"file too large (> {self.MAX_BYTES} bytes)"}

        # Magic checks per extension
        ok = False
        if ext == ".docx": ok = self._is_docx(data)
        elif ext == ".xlsx": ok = self._is_xlsx(data)
        elif ext == ".pptx": ok = self._is_pptx(data)
        elif ext == ".odt": ok = self._is_odt(data)
        elif ext == ".ods": ok = self._is_ods(data)
        elif ext == ".odp": ok = self._is_odp(data)
        elif ext == ".rtf": ok = self._is_rtf(data)
        elif ext == ".doc": ok = self._is_ole_doc(data)

        if not ok:
            return {"ok": False, "error": f"invalid or corrupted {ext} content"}

        # Save
        subdir = ym_subdir(self.ROOT)
        sha = sha256_hex(data)
        path = subdir / f"{sha[:16]}{ext}"
        if not path.exists():
            path.write_bytes(data)

        rel_path = str(path.relative_to(UPLOADS_ROOT)).replace("\\", "/")
        mime = self.MIME_MAP[ext]
        return {"ok": True, "rel_path": rel_path, "size": size, "sha256": sha, "mime": mime}
