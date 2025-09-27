# Path from repo root: fastapi\app\core\path_utils.py
from __future__ import annotations
from pathlib import Path

def as_path(obj) -> Path:
    """
    Normalize various path-like configs to a real filesystem Path.
    Supports:
      - pathlib.Path
      - str
      - Storage-like objects that expose .base_path or .directory
    """
    if isinstance(obj, Path):
        return obj
    if isinstance(obj, str):
        return Path(obj)

    base = getattr(obj, "base_path", None) or getattr(obj, "directory", None) or getattr(obj, "path", None)
    if base:
        return Path(base)

    raise TypeError(f"Expected filesystem path, got {type(obj).__name__}")