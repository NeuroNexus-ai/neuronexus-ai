# Path from repo root: streamlit\ui\auth\tokens.py

# streamlit/ui/auth/tokens.py
from __future__ import annotations
from typing import Dict, Optional, cast
import streamlit as st

_TOKEN_SS_KEY = "token_by_server"


def _token_map() -> Dict[str, Optional[str]]:
    """Return the current base_url->token map from session_state."""
    return cast(Dict[str, Optional[str]], st.session_state.get(_TOKEN_SS_KEY, {}))


def get_token(base_url: str) -> Optional[str]:
    """Get the token for a specific base_url, if any."""
    return _token_map().get(base_url)


def set_token(base_url: str, token: Optional[str]) -> None:
    """Set or clear the token for base_url in session_state."""
    tm = _token_map()
    if token:
        tm[base_url] = token
    else:
        tm.pop(base_url, None)
    st.session_state[_TOKEN_SS_KEY] = tm