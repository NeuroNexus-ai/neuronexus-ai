# Path from repo root: streamlit\ui\tabs\tab_users.py

from __future__ import annotations
from typing import Any, Dict, List, Optional
import streamlit as st

from core.state import get_current_base_url
from ui.utils import api_request, show_response  # موجود عندك
from ui.auth.tokens import get_token as get_access  # نظام auth الجديد (access per base_url)

def _auth_headers(base_url: str) -> Dict[str, str]:
    tok = get_access(base_url)
    return {"Authorization": f"Bearer {tok}"} if tok else {}

def _api(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"

def render(base_url: Optional[str] = None, feats: Optional[Dict[str, Any]] = None) -> None:
    if base_url is None:
        base_url = get_current_base_url()

    st.subheader("👥 Users")

    tabs = st.tabs(["List", "Create", "Edit / Actions", "Roles"])
    # ===== List =====
    with tabs[0]:
        c1, c2, c3 = st.columns([2,1,1])
        q = c1.text_input("Search (username/email)", "")
        page = c2.number_input("Page", 1, 9999, 1)
        page_size = c3.number_input("Page size", 1, 200, 20)

        if st.button("GET /users"):
            url = _api(base_url, "/users")
            r = api_request(
                "GET", base_url, url,  # utils.api_request عندك يتوقع (method, base_url, path_or_url, ...)
                params={"q": q or None, "page": int(page), "page_size": int(page_size)},
                headers=_auth_headers(base_url),
                require_auth=True,
            )
            show_response(r)

    # ===== Create =====
    with tabs[1]:
        with st.form("users_create"):
            u = st.text_input("Username")
            e = st.text_input("Email (optional)")
            p = st.text_input("Password", type="password")
            is_active = st.checkbox("Active", True)
            is_super = st.checkbox("Superuser", False)
            roles_csv = st.text_input("Roles (comma separated)", "")

            submitted = st.form_submit_button("POST /users")
            if submitted:
                url = _api(base_url, "/users")
                roles = [x.strip() for x in roles_csv.split(",") if x.strip()] or None
                payload = {
                    "username": u,
                    "email": (e or None),
                    "password": p,
                    "is_active": is_active,
                    "is_superuser": is_super,
                    "roles": roles,
                }
                r = api_request(
                    "POST", base_url, url,
                    json=payload,
                    headers=_auth_headers(base_url),
                    require_auth=True,
                )
                show_response(r)

    # ===== Edit / Actions =====
    with tabs[2]:
        st.caption("Quick actions on a single user")
        uid = st.number_input("User ID", min_value=1, step=1)

        c1, c2, c3, c4 = st.columns(4)
        if c1.button("GET /users/{id}"):
            r = api_request("GET", base_url, _api(base_url, f"/users/{int(uid)}"), headers=_auth_headers(base_url), require_auth=True)
            show_response(r)

        if c2.button("DELETE /users/{id}"):
            r = api_request("DELETE", base_url, _api(base_url, f"/users/{int(uid)}"), headers=_auth_headers(base_url), require_auth=True)
            show_response(r)

        with st.expander("PATCH /users/{id} (email/active/super/roles)"):
            e2 = st.text_input("New email (optional)", "")
            active2 = st.selectbox("is_active", [None, True, False], index=0)
            super2  = st.selectbox("is_superuser", [None, True, False], index=0)
            roles2  = st.text_input("Roles (comma separated) — leave empty to keep unchanged", "")

            if st.button("PATCH"):
                payload: Dict[str, Any] = {}
                if e2 != "":
                    payload["email"] = e2
                if active2 is not None:
                    payload["is_active"] = bool(active2)
                if super2 is not None:
                    payload["is_superuser"] = bool(super2)
                if roles2 != "":
                    payload["roles"] = [x.strip() for x in roles2.split(",") if x.strip()]

                r = api_request("PATCH", base_url, _api(base_url, f"/users/{int(uid)}"),
                                json=payload, headers=_auth_headers(base_url), require_auth=True)
                show_response(r)

        with st.expander("POST /users/{id}/password (reset)"):
            np = st.text_input("New password", type="password")
            if st.button("Reset password"):
                r = api_request("POST", base_url, _api(base_url, f"/users/{int(uid)}/password"),
                                json={"password": np}, headers=_auth_headers(base_url), require_auth=True)
                show_response(r)

    # ===== Roles =====
    with tabs[3]:
        if st.button("GET /users/roles/list"):
            r = api_request("GET", base_url, _api(base_url, "/users/roles/list"),
                            headers=_auth_headers(base_url), require_auth=True)
            show_response(r)