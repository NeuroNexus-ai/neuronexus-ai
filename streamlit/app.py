# Path from repo root: streamlit\app.py

# streamlit/app.py
from __future__ import annotations
import streamlit as st

from core.state import init_state, get_current_base_url
from core.capabilities import features_for          # ✅ أضف هذا
from ui.css import apply_css
from ui.sidebar import render_sidebar
from ui.tabs.tab_auth import render as render_tab_auth
from ui.tabs.tab_plugins import render as render_tab_plugins
from ui.tabs.tab_workflows import render as render_tab_workflows
from ui.tabs.tab_uploads import render as render_tab_uploads

st.set_page_config(page_title="NeuroNexus • Console", layout="wide")
apply_css()
init_state()

base_url = get_current_base_url()

# ✅ استدعِ الـ sidebar
with st.sidebar:
    render_sidebar()

# ✅ احسب القدرات قبل رسم التبويبات
try:
    feats = features_for(base_url)  # عادة ترجع dict فيه ما يدعمه السيرفر (auth/uploads/plugins/…)
except Exception as e:
    st.warning(f"Failed to fetch capabilities from server: {e}")
    feats = {}  # بديل آمن

st.title("NeuroNexus Console")

tabs = st.tabs(["🔐 Auth", "👥 Users", "🧩 Plugins", "⚙️ Workflows", "📤 Uploads"])
with tabs[0]:
    render_tab_auth(base_url)
with tabs[1]:
    render_tab_users(base_url, feats)
with tabs[2]:
    render_tab_plugins(base_url, feats)
with tabs[3]:
    render_tab_workflows(base_url, feats)
with tabs[4]:
    render_tab_uploads(base_url, feats)