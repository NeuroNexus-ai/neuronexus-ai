# Path from repo root: streamlit\ui\utils.py

# streamlit/ui/utils.py
from __future__ import annotations
from typing import Any, Dict, Optional
import streamlit as st

from core.http import request
from core.state import safe_json_input  # ✅ نعيد تصديرها هنا

__all__ = ["api_request", "show_response", "safe_json_input"]

def api_request(method: str, path: str, *, json_body: Optional[Dict[str, Any]] = None,
                base_url: Optional[str] = None, auth: bool = True):
    return request(method, path, data=json_body, base_url=base_url, auth=auth)

def show_response(resp) -> None:
    if resp is None:
        st.error("No response")
        return
    st.code(f"HTTP {resp.status_code}")
    try:
        st.json(resp.json())
    except Exception:
        st.text(resp.text)