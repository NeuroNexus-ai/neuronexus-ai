# Path from repo root: streamlit\ui\tabs\tab_plugins.py

# ui/tabs/tab_plugins.py
from __future__ import annotations
from typing import Optional, Dict
import streamlit as st
from ui.utils import api_request, show_response, safe_json_input
from core.capabilities import features_for

def render(base_url: str, feats: Optional[Dict] = None) -> None:
    """Plugins tab: list and run plugin tasks."""
    if feats is None:
        feats = features_for(base_url)

    st.subheader("🧩 Plugins")
    disabled = (not base_url) or (not feats.get("plugins", False))

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("GET /plugins", disabled=disabled, key="pl-list"):
            resp = api_request("GET", "/plugins", base_url=base_url, auth=False)
            show_response(resp)

    st.markdown("---")

    st.subheader("Run Plugin Task")
    name = st.text_input("Plugin name", value="pdf_reader", disabled=disabled, key="plg-name")
    task = st.text_input("Task", value="extract_text", disabled=disabled, key="plg-task")

    default_payload = {"rel_path": "pdf/sample.pdf", "return_text": True}
    payload = safe_json_input("Payload (JSON)", default_payload, key="plg-payload")

    can_run = not disabled and payload is not None and name.strip() and task.strip()
    if st.button("POST /plugins/{name}/{task}", disabled=not can_run, key="plg-run"):
        resp = api_request("POST", f"/plugins/{name}/{task}", json_body=payload or {}, base_url=base_url, auth=False)
        show_response(resp)