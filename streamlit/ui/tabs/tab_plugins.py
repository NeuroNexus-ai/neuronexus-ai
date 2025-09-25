# ui/tabs/tab_plugins.py
from __future__ import annotations

import streamlit as st
from core.api import api_request, show_response, safe_json_input


def render(container, base_url: str, feats: dict) -> None:
    """Plugins tab: list plugins + run a plugin task."""
    with container:
        st.subheader("Plugins")

        disabled = (not base_url) or (not feats.get("plugins", False))

        # List plugins
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("GET /plugins", disabled=disabled, key="pl-list"):
                resp = api_request("GET", "/plugins")
                show_response(resp)

        st.markdown("---")

        # Run specific plugin task
        st.subheader("Run Plugin Task")
        name = st.text_input("Plugin name", value="pdf_reader", disabled=disabled, key="plg-name")
        task = st.text_input("Task", value="extract_text", disabled=disabled, key="plg-task")

        default_payload = {"rel_path": "pdf/sample.pdf", "return_text": True}
        payload = safe_json_input("Payload (JSON)", default_payload, key="plg-payload")

        can_run = not disabled and payload is not None and name.strip() and task.strip()
        if st.button("POST /plugins/{name}/{task}", disabled=not can_run, key="plg-run"):
            resp = api_request("POST", f"/plugins/{name}/{task}", json_body=payload or {})
            show_response(resp)
