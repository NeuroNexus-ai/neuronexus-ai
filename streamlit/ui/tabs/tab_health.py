# Path from repo root: streamlit\ui\tabs\tab_health.py

# streamlit/ui/tabs/tab_health.py
from __future__ import annotations
import streamlit as st
from core.api import api_request, show_response

def render(container, base_url: str, feats: dict) -> None:
    with container:
        st.subheader("Health / Docs")
        disabled = (not base_url) or (not feats.get("root", False))

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("GET /", disabled=disabled, key="hi-root"):
                resp = api_request("GET", "/")
                show_response(resp)
        with c2:
            if st.button("GET /docs", disabled=disabled, key="hi-docs"):
                resp = api_request("GET", "/docs")
                st.write(resp.status_code); st.info("Open /docs in browser.")
        with c3:
            if st.button("GET /redoc", disabled=disabled, key="hi-redoc"):
                resp = api_request("GET", "/redoc")
                st.write(resp.status_code); st.info("Open /redoc in browser.")

        st.markdown("### Last Response (Debug)")
        last = getattr(st.session_state, "last_response", None)
        if last is not None:
            show_response(last)
        else:
            st.caption("No response saved yet.")