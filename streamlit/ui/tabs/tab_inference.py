# Path from repo root: streamlit\ui\tabs\tab_inference.py

# streamlit/ui/tabs/tab_inference.py
from __future__ import annotations
import streamlit as st
from core.api import api_request, show_response, safe_json_input

def render(container, base_url: str, feats: dict) -> None:
    with container:
        st.subheader("Inference (Unified)")
        disabled = (not base_url) or (not feats.get("inference", False))

        plugin = st.text_input("Plugin", value="pdf_reader", disabled=disabled, key="inf-plugin")
        task   = st.text_input("Task", value="extract_text", disabled=disabled, key="inf-task")
        payload = safe_json_input("Payload (JSON)", {"rel_path": "pdf/sample.pdf", "return_text": True}, key="inf-payload")
        if st.button("POST /inference", disabled=disabled or payload is None, key="inf-run"):
            resp = api_request("POST", "/inference", json_body={"plugin": plugin, "task": task, "payload": payload or {}})
            show_response(resp)