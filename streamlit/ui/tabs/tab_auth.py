from __future__ import annotations
from typing import Optional
import streamlit as st

from ..auth.ui import render as render_auth  # استيراد نسبي من حزمة المنطق

def render(container: st.delta_generator.DeltaGenerator, base_url: str, feats: Optional[dict] = None) -> None:
    with container:
        render_auth(base_url)
