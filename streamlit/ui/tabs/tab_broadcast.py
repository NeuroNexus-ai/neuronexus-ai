# Path from repo root: streamlit\ui\tabs\tab_broadcast.py

# streamlit/ui/tabs/tab_broadcast.py
from __future__ import annotations
import streamlit as st
from core.api import api_request, safe_json_input
from core.capabilities import supports

def render(container, base_url: str, feats: dict) -> None:
    with container:
        st.subheader("Broadcast request to all servers")
        req_path = st.text_input("Path", value="/info", key="bc-path")
        method = st.selectbox("Method", ["GET", "POST", "PUT", "DELETE"], index=0, key="bc-method")
        body = safe_json_input("Body (JSON) — Optional", {}, key="bc-body")

        if st.button("Send to all", key="bc-send"):
            servers = getattr(st.session_state, "servers", {})
            if not servers:
                st.warning("No servers to broadcast to.")
            else:
                for name, base in servers.items():
                    st.write(f"**{name}** → {base}")
                    if not supports(base, method, req_path):
                        st.info("Skipped (unsupported endpoint).")
                        continue
                    try:
                        resp = api_request(method, req_path, json_body=(body or None), base_url=base)
                        st.code(f"Status: {resp.status_code}")
                        try:
                            st.json(resp.json())
                        except Exception:
                            st.text(resp.text)
                    except Exception as e:
                        st.error(f"Failed: {e}")