# Path from repo root: streamlit\ui\auth\ui.py

# streamlit/ui/auth/ui.py
from __future__ import annotations
from typing import Optional

import streamlit as st

from .tokens import get_token, set_token
from .http import login_any, whoami_any, refresh, extract_access_token


def _show_current_status(base_url: str) -> None:
    col1, col2 = st.columns([1, 2])
    with col1:
        st.caption("Current server")
        st.code(base_url, language="text")
    with col2:
        token = get_token(base_url)
        st.caption("Token state")
        if token:
            st.success("Token loaded ✅")
            with st.expander("Show token (be careful)"):
                st.code(token, language="text")
        else:
            st.warning("No token stored")


def _login_form(base_url: str) -> None:
    st.subheader("🔐 Login")
    with st.form(key="auth_login", clear_on_submit=False):
        username = st.text_input("Username / Email", key="auth_user")
        password = st.text_input("Password", type="password", key="auth_pass")
        remember = st.checkbox("Remember token in session", value=True)
        submitted = st.form_submit_button("Login")

        if not submitted:
            return

        if not username or not password:
            st.error("يرجى إدخال بيانات الدخول.")
            return

        try:
            # يجرب JSON و FORM و /token تلقائيًا
            r = login_any(base_url, username, password)
            if r.ok:
                data = r.json()
                access = extract_access_token(data)  # يدعم access_token / token / data.access_token
                if not access:
                    st.warning("Login succeeded, but no access_token found in response.")
                else:
                    if remember:
                        set_token(base_url, access)
                    st.success("تم تسجيل الدخول ✅")
            else:
                st.error(f"فشل تسجيل الدخول: {r.status_code} — {r.text[:300]}")
        except Exception as exc:  # noqa: BLE001
            st.exception(exc)



def _who_am_i(base_url: str) -> None:
    st.subheader("👤 Who am I?")
    c1, c2 = st.columns([1, 1])

    with c1:
        if st.button("Call /auth/me"):
            try:
                r = whoami_any(base_url)  # ← بدل whoami
                if r.ok:
                    st.success("OK ✅")
                    st.json(r.json())
                else:
                    st.error(f"HTTP {r.status_code}")
                    st.code(r.text[:1000])
            except Exception as exc:  # noqa: BLE001
                st.exception(exc)

    with c2:
        if st.button("Logout (forget token)"):
            set_token(base_url, None)
            st.info("تم حذف التوكن من الجلسة.")



def _refresh_ui(base_url: str) -> None:
    st.subheader("♻️ Refresh token (optional)")
    refresh_token: Optional[str] = st.text_input("Refresh token (إن وجد)", key="auth_refresh")
    if st.button("Refresh"):
        try:
            r = refresh(base_url, refresh_token=refresh_token or None)
            if r.ok:
                data = r.json()
                new_access = data.get("access_token") or data.get("token")
                if new_access:
                    set_token(base_url, new_access)
                    st.success("تم تجديد التوكن ✅")
                else:
                    st.warning("Refresh response does not include access_token.")
                st.json(data)
            else:
                st.error(f"HTTP {r.status_code}")
                st.code(r.text[:1000])
        except Exception as exc:  # noqa: BLE001
            st.exception(exc)


def render(base_url: str) -> None:
    """Main Auth tab renderer."""
    st.header("🔑 Authentication")

    if not base_url:
        st.info("اختر سيرفر من الشريط الجانبي أولًا.")
        return

    _show_current_status(base_url)
    st.divider()
    _login_form(base_url)
    st.divider()
    _who_am_i(base_url)
    st.divider()
    _refresh_ui(base_url)