from __future__ import annotations
import streamlit as st
from typing import Dict, Optional, cast
from core.api import api_request, show_response

def render(container, base_url: str, feats: dict) -> None:
    with container:
        st.subheader("Login")
        disabled = (not base_url) or (not feats.get("auth", False))
        me_disabled = (not base_url) or (not feats.get("auth_me", False))

        col, _ = st.columns(2)
        with col:
            u = st.text_input("Username", disabled=disabled, key="auth-username")
            p = st.text_input("Password", type="password", disabled=disabled, key="auth-password")
            if st.button("POST /auth/login", disabled=disabled, key="auth-login"):
                resp = api_request("POST", "/auth/login", json_body={"username": u, "password": p})
                if resp.ok:
                    try:
                        data = resp.json()
                        token = data.get("access_token")
                        if token:
                            token_map = cast(Dict[str, Optional[str]], st.session_state["token_by_server"])
                            token_map[base_url.rstrip("/")] = token
                            st.success("Login successful ✅")
                    except Exception:
                        st.warning("Request succeeded but JSON parsing failed.")
                show_response(resp)

        st.markdown("---")
        st.subheader("GET /auth/me")
        if st.button("GET /auth/me", disabled=me_disabled, key="auth-me"):
            resp = api_request("GET", "/auth/me", require_auth=True)
            show_response(resp)
