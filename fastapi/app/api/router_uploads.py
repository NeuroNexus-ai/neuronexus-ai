from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.path_utils import as_path


router = APIRouter(prefix="/uploads", tags=["uploads"])


# ---------- Response Models ----------
class UploadResult(BaseModel):
    ok: bool = True
    rel_path: str = Field(..., description="Relative path under uploads/ (e.g., pdf/file.pdf)")
    size_bytes: int
    sha256: str | None = None
    mime: str | None = None


class FileItem(BaseModel):
    rel_path: str
    size_bytes: int


class ListResult(BaseModel):
    ok: bool = True
    files: list[FileItem] = []


# ---------- Helpers ----------
settings = get_settings()
UPLOAD_ROOT: Path = as_path(settings.UPLOAD_DIR).resolve()
PDF_ROOT: Path = UPLOAD_ROOT / "pdf"
PDF_ROOT.mkdir(parents=True, exist_ok=True)

MAX_MB = settings.UPLOAD_MAX_MB
ALLOWED_CT = {"application/pdf", "application/x-pdf", "application/acrobat"}

def _safe_dst(root: Path, name: str | None) -> Path:
    """
    Return a safe path inside the given root, preventing path traversal.

    Args:
        root (Path): The root directory where files are stored.
        name (str | None): The original filename.

    Returns:
        Path: A secure, resolved path under the root directory.

    Raises:
        HTTPException: If the resolved path is outside the root.
    """
    safe_name = Path(name or "upload.pdf").name
    dst = (root / safe_name).resolve()
    try:
        dst.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path")
    return dst


# ---------- Endpoints ----------
@router.post(
    "/pdf",
    response_model=UploadResult,
    summary="Upload a PDF",
    description="Uploads a PDF into uploads/pdf/ with soft content-type check and size limits.",
    status_code=status.HTTP_201_CREATED,
)
async def upload_pdf(file: Annotated[UploadFile, File(...)]):
    """
    Upload a PDF file to the uploads/pdf/ directory.

    Args:
        file (UploadFile): The file to upload.

    Returns:
        UploadResult: Metadata about the uploaded file.

    Raises:
        HTTPException: For invalid content types, empty files, or size limits exceeded.
    """
    if file.content_type and file.content_type.lower() not in ALLOWED_CT:
        pass

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    if len(data) > MAX_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File too large > {MAX_MB}MB")

    dst = _safe_dst(PDF_ROOT, file.filename)
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
    summary="List uploaded PDFs",
)
def list_pdfs():
    """
    List all uploaded PDF files.

    Returns:
        ListResult: A list of uploaded PDF files with metadata.
    """
    files = [
        FileItem(rel_path=f"pdf/{p.name}", size_bytes=p.stat().st_size)
        for p in PDF_ROOT.glob("*.pdf")
    ]
    return ListResult(files=files)


@router.get(
    "/pdf/{filename}",
    summary="Download a PDF by filename",
    responses={
        200: {"content": {"application/pdf": {}}},
        404: {"description": "File not found"},
    },
)
def get_pdf(filename: str):
    """
    Download a file from uploads/pdf/{filename}. Path traversal is prevented.

    Args:
        filename (str): The name of the file to download.

    Returns:
        FileResponse: The PDF file as a response.

    Raises:
        HTTPException: If the file is not found or not a PDF.
    """
    dst = _safe_dst(PDF_ROOT, filename)
    if not (dst.is_file() and dst.suffix.lower() == ".pdf"):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=str(dst),
        media_type="application/pdf",
        filename=dst.name,
    )
