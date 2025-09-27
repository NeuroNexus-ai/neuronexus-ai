# Path from repo root: fastapi\app\api\router_uploads.py
from __future__ import annotations

import hashlib
import mimetypes
import re
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.path_utils import as_path

router = APIRouter(prefix="/uploads", tags=["uploads"])

# ---------- Response Models ----------
class UploadResult(BaseModel):
    ok: bool = True
    rel_path: str = Field(
        ...,
        description="Relative path under uploads/ (e.g., image/photo.png, pdf/file.pdf, audio/voice.mp3, other/file.bin)",
    )
    size_bytes: int
    sha256: str | None = None
    mime: str | None = None


class FileItem(BaseModel):
    rel_path: str
    size_bytes: int


class ListResult(BaseModel):
    ok: bool = True
    files: list[FileItem] = []


# ---------- Setup / Helpers ----------
settings = get_settings()
UPLOAD_ROOT: Path = as_path(settings.UPLOAD_DIR).resolve()
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

# Max file size (in MB) from settings
MAX_MB: int = int(getattr(settings, "UPLOAD_MAX_MB", 25))

# Categories supported. Key = category folder under uploads/.
# Value = tuple: (predicate over content-type, human name)
Category = Literal["pdf", "image", "audio", "video", "text", "archive", "other"]
CATEGORY_RULES: list[tuple[Category, re.Pattern[str]]] = [
    ("pdf", re.compile(r"^application/(pdf|x-pdf|acrobat)$")),
    ("image", re.compile(r"^image/")),
    ("audio", re.compile(r"^audio/")),
    ("video", re.compile(r"^video/")),
    ("text", re.compile(r"^(text/|application/(json|xml|csv))")),
    ("archive", re.compile(r"^application/(zip|x-7z-compressed|x-rar-compressed|x-tar|x-gzip|x-bzip2|x-xz)$")),
]

def _category_from_ct(content_type: str | None, filename: str | None) -> Category:
    ct = (content_type or "").lower().strip()
    for cat, rx in CATEGORY_RULES:
        if rx.match(ct):
            return cat
    # fallback heuristics by extension
    suffix = (Path(filename or "").suffix.lower())
    if suffix == ".pdf":
        return "pdf"
    if suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff", ".svg"}:
        return "image"
    if suffix in {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".oga"}:
        return "audio"
    if suffix in {".mp4", ".mkv", ".mov", ".webm", ".avi"}:
        return "video"
    if suffix in {".txt", ".md", ".json", ".xml", ".csv", ".tsv"}:
        return "text"
    if suffix in {".zip", ".7z", ".rar", ".tar", ".gz", ".bz2", ".xz"}:
        return "archive"
    if suffix in {".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"}:
        return "docs"
    return "other"


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def _safe_dst(root: Path, name: str | None) -> Path:
    """
    Return a safe path inside the given root, preventing path traversal.
    """
    safe_name = Path(name or "upload.bin").name
    dst = (root / safe_name).resolve()
    try:
        dst.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path")
    return dst

def _dedupe_path(dst: Path) -> Path:
    """
    If the file exists, add a numeric suffix before the extension: file (1).ext, file (2).ext ...
    """
    if not dst.exists():
        return dst
    stem, suffix = dst.stem, dst.suffix
    parent = dst.parent
    i = 1
    while True:
        candidate = parent / f"{stem} ({i}){suffix}"
        if not candidate.exists():
            return candidate
        i += 1


# ---------- Endpoints (Generic) ----------
@router.post(
    "/",
    response_model=UploadResult,
    summary="Upload any file",
    description="Uploads any file under uploads/{category}/ with size limits and safe path handling.",
    status_code=status.HTTP_201_CREATED,
)
async def upload_file(file: Annotated[UploadFile, File(...)]):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    if len(data) > MAX_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File too large > {MAX_MB}MB")

    cat: Category = _category_from_ct(file.content_type, file.filename)
    root = (UPLOAD_ROOT / cat).resolve()
    _ensure_dir(root)

    dst = _safe_dst(root, file.filename)
    dst = _dedupe_path(dst)  # avoid overwriting existing files

    sha = hashlib.sha256(data).hexdigest()
    with open(dst, "wb") as f:
        f.write(data)

    rel = f"{root.name}/{dst.name}"
    return UploadResult(
        ok=True,
        rel_path=rel,
        size_bytes=len(data),
        sha256=sha,
        mime=file.content_type or mimetypes.guess_type(dst.name)[0] or "application/octet-stream",
    )


@router.get(
    "/{category}",
    response_model=ListResult,
    summary="List uploaded files by category",
)
def list_by_category(category: Category):
    root = (UPLOAD_ROOT / category).resolve()
    _ensure_dir(root)
    files = [
        FileItem(rel_path=f"{category}/{p.name}", size_bytes=p.stat().st_size)
        for p in root.iterdir()
        if p.is_file()
    ]
    return ListResult(files=files)


@router.get(
    "/{category}/{filename}",
    summary="Download a file by category + filename",
    responses={200: {"content": {"application/octet-stream": {}}}, 404: {"description": "File not found"}},
)
def download(category: Category, filename: str):
    root = (UPLOAD_ROOT / category).resolve()
    dst = _safe_dst(root, filename)
    if not dst.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    media_type = mimetypes.guess_type(dst.name)[0] or "application/octet-stream"
    return FileResponse(path=str(dst), media_type=media_type, filename=dst.name)


# ---------- Backward-compatible PDF routes (optional, can be removed later) ----------
# These keep old clients working: /uploads/pdf, /uploads/pdf/{filename}
@router.post(
    "/pdf",
    response_model=UploadResult,
    summary="[Deprecated] Upload a PDF",
    description="Use POST /uploads/ instead. This route remains for backward compatibility.",
    status_code=status.HTTP_201_CREATED,
)
async def upload_pdf_backward(file: Annotated[UploadFile, File(...)]):
    # force pdf category but still reuse the generic uploader logic
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > MAX_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File too large > {MAX_MB}MB")

    root = (UPLOAD_ROOT / "pdf").resolve()
    _ensure_dir(root)
    dst = _safe_dst(root, file.filename)
    dst = _dedupe_path(dst)
    sha = hashlib.sha256(data).hexdigest()
    with open(dst, "wb") as f:
        f.write(data)
    rel = f"pdf/{dst.name}"
    return UploadResult(
        ok=True,
        rel_path=rel,
        size_bytes=len(data),
        sha256=sha,
        mime=file.content_type or "application/pdf",
    )


@router.get(
    "/pdf",
    response_model=ListResult,
    summary="[Deprecated] List uploaded PDFs",
)
def list_pdfs_backward():
    root = (UPLOAD_ROOT / "pdf").resolve()
    _ensure_dir(root)
    files = [
        FileItem(rel_path=f"pdf/{p.name}", size_bytes=p.stat().st_size)
        for p in root.glob("*.pdf")
    ]
    return ListResult(files=files)


@router.get(
    "/pdf/{filename}",
    summary="[Deprecated] Download a PDF by filename",
    responses={200: {"content": {"application/pdf": {}}}, 404: {"description": "File not found"}},
)
def get_pdf_backward(filename: str):
    root = (UPLOAD_ROOT / "pdf").resolve()
    dst = _safe_dst(root, filename)
    if not (dst.is_file() and dst.suffix.lower() == ".pdf"):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=str(dst), media_type="application/pdf", filename=dst.name)