# ui/tabs/__init__.py
from __future__ import annotations
import streamlit as st

from . import tab_broadcast, tab_health, tab_inference, tab_uploads, tab_workflows

__all__ = ["render_all_tabs"]

def render_all_tabs(base_url: str, feats: dict | None = None) -> None:
    st.title("NeuroNexus-ai Dashboard (Multi-Server)")
    st.caption(
        "Professional interface for managing multiple FastAPI servers: "
        "Add/Edit/Delete · Independent Tokens · Request Broadcasting"
    )

    tabs = st.tabs(
        ["Auth", "Uploads", "Plugins", "Inference", "Workflows", "Health/Info", "Broadcast"]
    )

    from . import tab_auth, tab_plugins

    tab_auth.render(tabs[0], base_url, feats)
    tab_uploads.render(tabs[1], base_url, feats)
    tab_plugins.render(tabs[2], base_url, feats)
    tab_inference.render(tabs[3], base_url, feats)
    tab_workflows.render(tabs[4], base_url, feats)
    tab_health.render(tabs[5], base_url, feats)
    tab_broadcast.render(tabs[6], base_url, feats)
