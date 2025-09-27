# Path from repo root: fastapi\app\services\text_tools\service.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from app.services.base import BaseService

UPLOADS_ROOTS: tuple[Path, ...] = (
    Path("fastapi") / "uploads",
    Path("uploads"),
    Path("app") / "uploads",
    Path("data") / "uploads",
)

@dataclass
class SaveOpts:
    rel_path: str | None = None
    dir: str | None = None
    filename: str | None = None
    append: bool = False
    ensure_unique: bool = False
    encoding: str = "utf-8"
    newline: str | None = None
    bom: bool = False
    normalize: dict | None = None

class Service(BaseService):
    name = "text_tools"
    tasks = ["save_text"]

    def _uploads_base(self) -> Path:
        for r in UPLOADS_ROOTS:
            if r.exists():
                return r
        return UPLOADS_ROOTS[0]

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        bad = '<>:"/\\|?*'
        return "".join("_" if c in bad else c for c in name).strip()

    @staticmethod
    def _normalize_text(txt: str, opts: dict | None) -> str:
        if not opts:
            return txt
        if opts.get("strip", True):
            txt = txt.strip()
        if opts.get("collapse_spaces", False):
            txt = "\n".join(" ".join(line.split()) for line in txt.splitlines())
        return txt

    @staticmethod
    def _ensure_unique_path(p: Path) -> Path:
        if not p.exists():
            return p
        stem, suf = p.stem, p.suffix
        i = 1
        while True:
            cand = p.with_name(f"{stem}({i}){suf}")
            if not cand.exists():
                return cand
            i += 1

    def save_text(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return {"ok": False, "error": "payload must be an object"}
        text = payload.get("text")
        if not isinstance(text, str):
            return {"ok": False, "error": "text is required (string)"}

        opts = SaveOpts(
            rel_path=payload.get("rel_path"),
            dir=payload.get("dir"),
            filename=payload.get("filename"),
            append=bool(payload.get("append", False)),
            ensure_unique=bool(payload.get("ensure_unique", False)),
            encoding=str(payload.get("encoding", "utf-8")),
            newline=payload.get("newline"),
            bom=bool(payload.get("bom", False)),
            normalize=payload.get("normalize"),
        )

        base = self._uploads_base()
        if opts.rel_path:
            out_path = (base / opts.rel_path).resolve()
        else:
            out_dir = base / (opts.dir or "text")
            out_name = self._sanitize_filename(opts.filename or "output.txt")
            out_path = (out_dir / out_name).resolve()

        out_path.parent.mkdir(parents=True, exist_ok=True)
        if opts.ensure_unique and out_path.exists():
            out_path = self._ensure_unique_path(out_path)

        text = self._normalize_text(text, opts.normalize)
        if opts.newline in {"\n", "\r\n"}:
            text = text.replace("\r\n", "\n").replace("\r", "\n")
            if opts.newline == "\r\n":
                text = text.replace("\n", "\r\n")

        mode = "ab" if opts.append else "wb"
        data = text.encode(opts.encoding, errors="replace")
        if (not opts.append) and opts.bom and opts.encoding.lower().replace("-", "") == "utf8":
            data = b"\xef\xbb\xbf" + data

        with open(out_path, mode) as f:
            f.write(data)

        return {"ok": True, "saved_to": str(out_path), "bytes_written": len(data)}