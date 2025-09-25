from __future__ import annotations
from pathlib import Path
import streamlit as st
from core.constants import CSS_PATH

@st.cache_data
def _load_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")

def apply_css() -> None:
    path = CSS_PATH
    if path.exists():
        st.markdown(f"<style>{_load_text(str(path))}</style>", unsafe_allow_html=True)
    else:
        st.warning(f"CSS file not found: {path}")
