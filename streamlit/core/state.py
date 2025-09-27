# streamlit/core/state.py
from __future__ import annotations
import json
from typing import Any, Dict, Optional, Tuple
import streamlit as st

# -----------------------------
# Session State Initialization
# -----------------------------
def init_state() -> None:
    # لا نضع type hints على st.session_state.<attr> بسبب Pylance
    if "servers" not in st.session_state:
        st.session_state.servers = {
            "local": "http://127.0.0.1:8000",  # default server
        }
    if "selected_server" not in st.session_state:
        st.session_state.selected_server = "local"
    if "token_by_server" not in st.session_state:
        # { server_key: {"access": str|None, "refresh": str|None, "exp": str|None} }
        st.session_state.token_by_server = {}

# اجعل الحالة جاهزة حتى لو لم تُستدعَ init_state من الخارج
init_state()

# -----------------------------
# Servers helpers
# -----------------------------
def servers() -> Dict[str, str]:
    return dict(st.session_state.servers)

def set_server(key: str, url: str) -> None:
    st.session_state.servers[key] = url

def selected_server_key() -> str:
    return st.session_state.selected_server

def set_selected_server(key: str) -> None:
    if key in st.session_state.servers:
        st.session_state.selected_server = key

def selected_base_url() -> str:
    key = selected_server_key()
    return st.session_state.servers.get(key, "http://127.0.0.1:8000")

def get_current_base_url() -> str:
    return selected_base_url()

# -----------------------------
# Tokens helpers (per-server)
# -----------------------------
def _ensure_tokens() -> None:
    if "token_by_server" not in st.session_state:
        st.session_state.token_by_server = {}

def set_token_for(server_key: str, access: Optional[str],
                  refresh: Optional[str] = None, exp: Optional[str] = None) -> None:
    _ensure_tokens()
    if access:
        st.session_state.token_by_server[server_key] = {
            "access": access, "refresh": refresh, "exp": exp
        }
    else:
        st.session_state.token_by_server.pop(server_key, None)

def token_for(server_key: Optional[str] = None) -> Optional[str]:
    _ensure_tokens()
    if server_key is None:
        server_key = selected_server_key()
    entry = st.session_state.token_by_server.get(server_key)
    return entry.get("access") if entry else None

def refresh_token_for(server_key: Optional[str] = None) -> Optional[str]:
    _ensure_tokens()
    if server_key is None:
        server_key = selected_server_key()
    entry = st.session_state.token_by_server.get(server_key)
    return entry.get("refresh") if entry else None

def clear_token_for(server_key: Optional[str] = None) -> None:
    _ensure_tokens()
    if server_key is None:
        server_key = selected_server_key()
    st.session_state.token_by_server.pop(server_key, None)

def token_bundle_for(server_key: Optional[str] = None) -> Optional[Dict[str, Optional[str]]]:
    _ensure_tokens()
    if server_key is None:
        server_key = selected_server_key()
    return st.session_state.token_by_server.get(server_key)

# -----------------------------
# Backward-compat helpers
# -----------------------------
def no_selection() -> Dict[str, Optional[str]]:
    return {"key": None, "url": None}

def safe_json_input(label: str, default_value: Any = None,
                    key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    حقل إدخال JSON آمن: يقبل dict (أو str) ويعيد dict أو None مع تحذير إذا JSON غير صالح.
    """
    import json as _json
    default_text = _json.dumps(default_value, ensure_ascii=False, indent=2) if isinstance(default_value, (dict, list)) else (default_value or "{}")
    txt = st.text_area(label, value=default_text, key=key)
    if not txt.strip():
        return None
    try:
        return _json.loads(txt)
    except Exception:
        st.warning("Invalid JSON")
        return None
