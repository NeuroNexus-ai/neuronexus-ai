from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from app.services.base import BaseService

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

try:
    from PyPDF2 import PdfReader
except Exception:
    PdfReader = None


class Service(BaseService):
    name = "pdf_reader"
    tasks = ["extract_text"]

    def extract_text(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract text from a PDF file located in the 'uploads/pdf' directory.

        Args:
            payload (Dict[str, Any]): A dictionary containing the key 'rel_path',
                which is the relative path to the PDF file.

        Returns:
            Dict[str, Any]: A dictionary containing either the extracted text with 'ok': True,
            or an error message with 'ok': False.

        Notes:
            - Requires either PyMuPDF (fitz) or PyPDF2 to be installed.
            - Returns an error if the file is not found or neither library is available.
        """
        rel_path = payload.get("rel_path")
        if not rel_path:
            return {"ok": False, "error": "rel_path is required"}

        file_path = Path("uploads/pdf") / rel_path
        if not file_path.is_file():
            return {"ok": False, "error": f"File not found: {file_path}"}

        if fitz is None and PdfReader is None:
            return {"ok": False, "error": "Neither PyMuPDF nor PyPDF2 is installed."}

        text = ""
        try:
            if fitz:
                doc = fitz.open(file_path)
                text = "\n".join(page.get_text() for page in doc)
            elif PdfReader:
                reader = PdfReader(str(file_path))
                text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            return {"ok": False, "error": str(e)}

        return {"ok": True, "text": text}