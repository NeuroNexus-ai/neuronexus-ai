# streamlit/core/api.py
from __future__ import annotations
import json, requests, streamlit as st
from typing import Any, Dict, Optional
from core.state import no_selection, token_for

def api_request(
    method: str,
    path: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    files: Optional[Dict[str, Any]] = None,
    require_auth: bool = False,
    base_url: Optional[str] = None,
) -> requests.Response:
    if not base_url:
        if no_selection():
            st.error("No server selected. Add/select a server from the sidebar first.")
            raise RuntimeError("No server selected")
        base_url = st.session_state.servers[st.session_state.selected_server]

    base = base_url.rstrip("/")
    url = f"{base}/{path.lstrip('/')}"
    headers = {"Accept": "application/json"}

    token = token_for(base)
    if require_auth and token:
        headers["Authorization"] = f"Bearer {token}"

    resp = requests.request(
        method.upper(),
        url,
        params=params,
        json=json_body,
        files=files,
        headers=headers,
        timeout=60,
    )
    st.session_state.last_response = resp
    return resp

def show_response(resp: requests.Response) -> None:
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(f"**Status:** `{resp.status_code}`")
        try:
            st.json(resp.json())
        except Exception:
            st.code(resp.text or "<no body>")
    with col2:
        st.markdown("**Headers:**")
        try:
            st.code(json.dumps(dict(resp.headers), indent=2, ensure_ascii=False))
        except Exception:
            st.code(str(resp.headers))

def safe_json_input(label: str, default: dict | list | None = None, *, key: Optional[str] = None):
    text = json.dumps(default or {}, ensure_ascii=False, indent=2)
    txt = st.text_area(label, value=text, height=180, key=key)
    if not txt.strip():
        return None
    try:
        return json.loads(txt)
    except json.JSONDecodeError as e:
        st.error(f"Invalid JSON: {e}")
        return None
