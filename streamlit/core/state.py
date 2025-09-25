from __future__ import annotations
from typing import Any, Dict, Optional, cast
import streamlit as st
from core.storage import load_servers_from_disk
from core.capabilities import features_for

def init_state() -> None:
    if "servers" not in st.session_state:
        st.session_state.servers = load_servers_from_disk()
    if "selected_server" not in st.session_state:
        st.session_state.selected_server = ""
    if "token_by_server" not in st.session_state:
        st.session_state["token_by_server"] = {}  # base_url -> token
    if "last_response" not in st.session_state:
        st.session_state.last_response = None

def no_selection() -> bool:
    return (not st.session_state.selected_server) or (
        st.session_state.selected_server not in st.session_state.servers
    )

def current_base_and_feats():
    if no_selection():
        return "", {}
    base = st.session_state.servers.get(st.session_state.selected_server, "")
    feats = features_for(base) if base else {}
    return base, feats

def token_for(base: str) -> Optional[str]:
    token_map = cast(Dict[str, Optional[str]], st.session_state["token_by_server"])
    return token_map.get(base)
