# Path from repo root: streamlit\ui\tabs\tab_auth.py

# streamlit/ui/tabs/tab_auth.py
from __future__ import annotations
import streamlit as st

# نستخدم نفس مصدر الـ Base URL حتى نحافظ على التوافق مع بقية التبويبات
from core.state import get_current_base_url

# نحاول استيراد الواجهة الجديدة
try:
    from ui.auth.ui import render as render_auth  # الواجهة الجديدة
except Exception as e:  # نعرض خطأ واضح لو الاستيراد فشل
    render_auth = None
    _import_error = e

def render(base_url: str | None = None):
    """
    Wrapper متوافق مع التوقيع القديم:
    - يُبقي استدعاء render(base_url=None) كما كان
    - يمرّر base_url للواجهة الجديدة
    """
    if base_url is None:
        base_url = get_current_base_url()

    if render_auth is None:
        st.error(f"Failed to load new Auth UI (ui.auth.ui): {type(_import_error).__name__}: {_import_error}")
        st.info("Tip: تأكد أن المسار 'streamlit/ui/auth/ui.py' موجود وأنه لا يحتوي أخطاء استيراد.")
        return

    # استدعاء الواجهة الجديدة 1:1
    render_auth(base_url=base_url)