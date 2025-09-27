# ui/tabs/tab_workflows.py
from __future__ import annotations
from typing import Optional, Dict
import streamlit as st
from ui.utils import api_request, show_response, safe_json_input
from core.capabilities import features_for

def render(base_url: str, feats: Optional[Dict] = None) -> None:
    """Workflows tab: list & run workflows."""
    if feats is None:
        feats = features_for(base_url)

    st.subheader("⚙️ Workflows")
    disabled = (not base_url) or (not feats.get("workflows", False))

    wf_name = st.text_input("Workflow name", value="asr_clean_ar", disabled=disabled, key="wf-name")
    wf_inputs = safe_json_input("Inputs (JSON)", {"text": "Hello", "lang": "ar"}, key="wf-inputs")

    if st.button("POST /workflows/run", disabled=disabled or wf_inputs is None, key="wf-run"):
        body = {"name": wf_name, "inputs": wf_inputs or {}}
        resp = api_request("POST", "/workflows/run", json_body=body, base_url=base_url, auth=False)
        show_response(resp)

    st.markdown("---")
    if st.button("GET /workflows", disabled=disabled, key="wf-list"):
        resp = api_request("GET", "/workflows", base_url=base_url, auth=False)
        show_response(resp)
