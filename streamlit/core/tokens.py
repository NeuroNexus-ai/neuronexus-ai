# streamlit/core/tokens.py
from __future__ import annotations
from typing import Any, Dict, Optional, Union
import streamlit as st

TokenDict = Dict[str, Any]

def _ensure() -> TokenDict:
    """Ensure the token map exists in session_state and return it."""
    if "token_by_server" not in st.session_state:
        st.session_state["token_by_server"] = {}
    return st.session_state["token_by_server"]  # type: ignore[return-value]

def get_token(server_key: str) -> Optional[TokenDict]:
    """Get stored token object for a server (or None)."""
    m = _ensure()
    tok = m.get(server_key)
    return tok if isinstance(tok, dict) else None

def set_token(
    server_key: str,
    token_or_access: Union[TokenDict, str, None],
    refresh: Optional[str] = None,
    exp: Optional[Any] = None,
) -> None:
    """
    Backward-compatible setter:
      - set_token(server, {"access": "...", "refresh": "...", "exp": ...})
      - set_token(server, access, refresh, exp)
      - set_token(server, None)  -> remove
    """
    m = _ensure()

    # Remove / clear
    if token_or_access is None or (isinstance(token_or_access, str) and token_or_access.strip() == ""):
        m.pop(server_key, None)
        st.session_state["token_by_server"] = m
        return

    if isinstance(token_or_access, dict):
        token: TokenDict = {
            "access": token_or_access.get("access") or token_or_access.get("access_token"),
            "refresh": token_or_access.get("refresh") or token_or_access.get("refresh_token"),
            "exp": token_or_access.get("exp") or token_or_access.get("expires_in"),
        }
    else:
        # token_or_access is a string (access token)
        token = {"access": token_or_access, "refresh": refresh, "exp": exp}

    if not token.get("access"):
        # إذا ما في access لا نخزّن شيء
        m.pop(server_key, None)
    else:
        m[server_key] = token

    st.session_state["token_by_server"] = m

def clear_token(server_key: str) -> None:
    """Remove stored token for a server."""
    m = _ensure()
    m.pop(server_key, None)
    st.session_state["token_by_server"] = m

def has_token(server_key: str) -> bool:
    """Convenience check."""
    t = get_token(server_key)
    return bool(t and t.get("access"))

def access_token(server_key: str) -> Optional[str]:
    """Get only the access token string (or None)."""
    t = get_token(server_key)
    return t.get("access") if t else None
