# Path from repo root: streamlit\ui\sidebar.py

# streamlit/ui/sidebar.py
from __future__ import annotations
import streamlit as st
from core.state import set_server, get_current_base_url
from core.http import health

def render_sidebar():
    st.subheader("Server")
    servers = st.session_state.servers
    keys = list(servers.keys())
    sel = st.selectbox("Select server", options=keys, index=keys.index(st.session_state.selected_server))
    st.session_state.selected_server = sel

    new_url = st.text_input("Base URL", value=servers[sel], help="e.g. http://127.0.0.1:8000")
    if new_url != servers[sel]:
        set_server(sel, new_url)

    c1, c2, c3 = st.columns(3)
    if c1.button("Test"):
        ok = health(get_current_base_url())
        st.success("OK ✅") if ok else st.error("Unreachable ❌")

    if c2.button("Docs"):
        st.markdown(f"[Open Docs]({get_current_base_url().rstrip('/')}/docs)", unsafe_allow_html=True)

    if c3.button("Reload UI"):
        st.rerun()