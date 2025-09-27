# Path from repo root: streamlit\ui\auth\http.py

# streamlit/ui/auth/http.py
from __future__ import annotations
from typing import Dict, Optional, Any, Iterable
import requests

from .tokens import get_token

def api(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"

def auth_headers(base_url: str) -> Dict[str, str]:
    tok = get_token(base_url)
    return {"Authorization": f"Bearer {tok}"} if tok else {}


def _try_endpoints(
    base_url: str,
    candidates: Iterable[tuple[str, str, Dict[str, Any]]],
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 10,
) -> requests.Response:
    """
    جرّب عدة endoints/أنماط. يرجع أول رد ناجح (2xx).
    لو الرد 422/415/400 (شكل الطلب غير صحيح) يكمل للمحاولة التالية.
    لو الرد 401 (اعتماد خاطئ) يرجّع مباشرة (ما في داعي نجرب مسارات أخرى).
    وإلا يحتفظ بآخر رد ويرجّعه في النهاية.
    """
    last_resp: Optional[requests.Response] = None
    last_exc: Optional[Exception] = None

    for method, path, payload in candidates:
        url = api(base_url, path)
        try:
            if method == "POST_JSON":
                resp = requests.post(url, json=payload, headers=headers or {}, timeout=timeout)
            elif method == "POST_FORM":
                resp = requests.post(url, data=payload, headers=headers or {}, timeout=timeout)
            elif method == "GET":
                resp = requests.get(url, headers=headers or {}, timeout=timeout)
            else:
                continue

            # نجاح
            if 200 <= resp.status_code < 300:
                return resp

            # أخطاء شكل الطلب → جرّب التالي
            if resp.status_code in {400, 415, 422}:
                last_resp = resp
                continue

            # اعتماد خاطئ → ارجع فورًا
            if resp.status_code == 401:
                return resp

            # أي شيء آخر: خزّنه وكمل (قد تنجح محاولات لاحقة)
            last_resp = resp

        except Exception as exc:  # noqa: BLE001
            last_exc = exc

    if last_resp is not None:
        return last_resp
    if last_exc:
        raise last_exc
    raise RuntimeError("No endpoints tried")


def login_any(base_url: str, username: str, password: str, timeout: int = 10) -> requests.Response:
    """
    يجرب تلقائياً:
      - /auth/login JSON
      - /auth/login FORM (username/password)  ← هذا المطلوب عندك
      - /token FORM بأسلوب OAuth2 (للأنظمة الشبيهة)
    """
    candidates: list[tuple[str, str, Dict[str, Any]]] = [
        ("POST_JSON", "/auth/login", {"username": username, "password": password}),
        ("POST_FORM", "/auth/login", {"username": username, "password": password}),
        ("POST_FORM", "/token", {
            "username": username,
            "password": password,
            "grant_type": "password",
            "scope": "",
            "client_id": "",
            "client_secret": "",
        }),
    ]
    return _try_endpoints(base_url, candidates, timeout=timeout)


def whoami_any(base_url: str, timeout: int = 10) -> requests.Response:
    return _try_endpoints(
        base_url,
        candidates=[
            ("GET", "/auth/me", {}),
            ("GET", "/users/me", {}),
        ],
        headers=auth_headers(base_url),
        timeout=timeout,
    )

def refresh(base_url: str, refresh_token: Optional[str] = None, timeout: int = 10) -> requests.Response:
    payload: Dict[str, Any] = {}
    if refresh_token:
        payload["refresh_token"] = refresh_token
    url = api(base_url, "/auth/refresh")
    return requests.post(url, json=payload, headers=auth_headers(base_url), timeout=timeout)

def extract_access_token(data: Dict[str, Any]) -> Optional[str]:
    """يدعم عدة أشكال للرد."""
    return (
        data.get("access_token")
        or data.get("token")
        or (data.get("data") or {}).get("access_token")
    )