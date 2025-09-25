from __future__ import annotations
import streamlit as st
from core.api import api_request, show_response, safe_json_input

def render(container, base_url: str, feats: dict) -> None:
    with container:
        st.subheader("Workflows")
        disabled = (not base_url) or (not feats.get("workflows", False))

        wf_name = st.text_input("Workflow name", value="asr_clean_ar", disabled=disabled, key="wf-name")
        wf_inputs = safe_json_input("Inputs (JSON)", {"text": "Hello", "lang": "ar"}, key="wf-inputs")
        if st.button("POST /workflows/run", disabled=disabled or wf_inputs is None, key="wf-run"):
            resp = api_request("POST", "/workflows/run", json_body={"name": wf_name, "inputs": wf_inputs or {}})
            show_response(resp)

        st.markdown("---")
        if st.button("GET /workflows", disabled=disabled, key="wf-list"):
            resp = api_request("GET", "/workflows")
            show_response(resp)
