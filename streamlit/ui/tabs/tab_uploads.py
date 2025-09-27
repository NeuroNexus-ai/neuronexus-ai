# Path from repo root: streamlit\ui\tabs\tab_uploads.py

# ui/tabs/tab_uploads.py
from __future__ import annotations
from typing import Optional, Dict
import streamlit as st
from core.capabilities import features_for
from ui.utils import api_request, show_response
from core.state import safe_json_input  # إذا كنت تستخدمه

def render(base_url: str, feats: Optional[Dict] = None) -> None:
    if feats is None:
        feats = features_for(base_url)

    st.subheader("📤 Uploads")
    disabled = (not base_url) or (not feats.get("uploads", False))

    # مثال بسيط لاستدعاء الرفع
    uploaded = st.file_uploader("Choose a file", disabled=disabled)
    if uploaded and st.button("POST /uploads", disabled=disabled):
        files = {"file": (uploaded.name, uploaded.getvalue())}
        # ملاحظة: api_request في utils حالياً يرسل JSON فقط.
        # لو عندك endpoint رفع multipart، استخدم requests مباشرة أو وسّع api_request لدعم files.
        import requests
        url = f"{base_url.rstrip('/')}/uploads"
        try:
            resp = requests.post(url, files=files, timeout=30)
            show_response(resp)
        except Exception as e:
            st.error(f"Upload failed: {e}")