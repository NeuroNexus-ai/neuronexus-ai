# Path from repo root: streamlit\core\http.py

# streamlit/core/http.py
from __future__ import annotations
from typing import Any, Dict, Optional, Tuple
import requests

from core.tokens import get_token, set_token


# ========================
# Helpers
# ========================

def _api(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"

def _bearer(access: Optional[str]) -> Dict[str, str]:
    return {"Authorization": f"Bearer {access}"} if access else {}


# ========================
# Auth Endpoints
# ========================

def login(base_url: str, server_key: str, username: str, password: str) -> bool:
    """
    FastAPI endpoint expects application/x-www-form-urlencoded with grant_type=password.
    """
    url = _api(base_url, "/auth/login")
    try:
        resp = requests.post(
            url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "password",
                "username": username,
                "password": password,
            },
            timeout=15,
        )
        if not resp.ok:
            return False

        data = resp.json()
        # نقبل تسميات متعددة للحقل
        access = data.get("access") or data.get("access_token")
        refresh = data.get("refresh") or data.get("refresh_token")
        exp = data.get("exp") or data.get("expires_in")

        if not access:
            return False

        set_token(server_key, access, refresh, exp)
        return True
    except Exception:
        return False


def whoami(base_url: str, server_key: str) -> Optional[Dict[str, Any]]:
    url = _api(base_url, "/auth/me")
    tok = get_token(server_key) or {}
    access = tok.get("access") if isinstance(tok, dict) else None
    if not access:
        return None
    try:
        r = requests.get(url, headers=_bearer(access), timeout=15)
        return r.json() if r.ok else None
    except Exception:
        return None


def refresh(base_url: str, server_key: str) -> bool:
    """
    يحاول أولاً JSON ثم يسقط إلى x-www-form-urlencoded.
    يحدّث التوكنات المخزّنة عند النجاح.
    """
    tok = get_token(server_key) or {}
    refresh_token = tok.get("refresh") if isinstance(tok, dict) else None
    if not refresh_token:
        return False

    url = _api(base_url, "/auth/refresh")
    try:
        r = requests.post(url, json={"refresh": refresh_token}, timeout=15)
        if r.status_code in (415, 422) or not r.ok:
            r = requests.post(
                url,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={"refresh": refresh_token},
                timeout=15,
            )
        if not r.ok:
            return False

        data = r.json()
        access = data.get("access") or data.get("access_token")
        new_refresh = data.get("refresh") or data.get("refresh_token") or refresh_token
        exp = data.get("exp") or data.get("expires_in")

        if not access:
            return False

        set_token(server_key, access, new_refresh, exp)
        return True
    except Exception:
        return False


# ========================
# Health Check
# ========================

def health(base_url: str, path: str = "/health", timeout: int = 5) -> Tuple[bool, str]:
    """
    يفحص /health ويعيد (is_ok, message).
    """
    url = _api(base_url, path)
    try:
        r = requests.get(url, timeout=timeout)
        if r.ok:
            try:
                j = r.json()
                msg = str(j.get("status") or j.get("message") or j)
            except Exception:
                msg = (r.text or "ok")[:200]
            return True, msg
        else:
            return False, f"{r.status_code} {r.text[:200]}"
    except Exception as e:
        return False, str(e)


# ========================
# Generic Request Helpers
# ========================

def request(
    method: str,
    base_url: str,
    path: str,
    *,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    json: Any = None,
    data: Any = None,
    files: Any = None,
    timeout: int = 30,
) -> requests.Response:
    """
    Shim عام ليستخدمه UI: يبني URL ويستدعي requests.<method>.
    يعيد كائن Response كما هو (لا raise_for_status هنا).
    """
    url = _api(base_url, path)
    m = method.upper().strip()
    return requests.request(
        method=m,
        url=url,
        headers=headers,
        params=params,
        json=json,
        data=data,
        files=files,
        timeout=timeout,
    )


def api_request(
    method: str,
    base_url: str,
    path: str,
    **kwargs: Any,
) -> requests.Response:
    """
    مثل request لكن يرفع خطأ لو لم تكن الاستجابة 2xx.
    """
    resp = request(method, base_url, path, **kwargs)
    resp.raise_for_status()
    return resp