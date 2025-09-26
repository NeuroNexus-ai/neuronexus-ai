# ui/tabs/__init__.py
from __future__ import annotations
import streamlit as st

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

    from . import tab_auth, uploads, tab_plugins, inference, workflows, health, broadcast

    tab_auth.render(tabs[0], base_url, feats)
    uploads.render(tabs[1], base_url, feats)
    tab_plugins.render(tabs[2], base_url, feats)
    inference.render(tabs[3], base_url, feats)
    workflows.render(tabs[4], base_url, feats)
    health.render(tabs[5], base_url, feats)
    broadcast.render(tabs[6], base_url, feats)
