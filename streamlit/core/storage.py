# streamlit/core/storage.py
from __future__ import annotations
import json
from typing import Dict
from core.constants import STREAMLIT_DIR, SERVERS_STORE

def ensure_dirs() -> None:
    STREAMLIT_DIR.mkdir(parents=True, exist_ok=True)

def load_servers_from_disk() -> Dict[str, str]:
    if SERVERS_STORE.exists():
        try:
            data = json.loads(SERVERS_STORE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
        except Exception:
            pass
    return {}

def save_servers_to_disk(servers: Dict[str, str]) -> None:
    ensure_dirs()
    SERVERS_STORE.write_text(
        json.dumps(servers, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
