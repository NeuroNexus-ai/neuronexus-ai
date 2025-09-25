from __future__ import annotations
from typing import Optional, Dict
import re, requests
import streamlit as st

@st.cache_data(ttl=60)
def fetch_openapi(base_url: str) -> Optional[dict]:
    if not base_url:
        return None
    try:
        r = requests.get(base_url.rstrip("/") + "/openapi.json", timeout=6)
        if r.ok:
            return r.json()
    except Exception:
        pass
    return None

def _path_to_regex(template: str):
    esc = re.escape(template)
    pattern = re.sub(r"\\{[^/]+?\\}", r"[^/]+", esc)
    return re.compile("^" + pattern + "$")

def build_caps(openapi: Optional[dict]) -> Dict[str, set]:
    caps: Dict[str, set] = {m: set() for m in ("GET","POST","PUT","DELETE","PATCH")}
    if not openapi or "paths" not in openapi:
        return caps
    for pth, item in openapi["paths"].items():
        for m in caps:
            if item.get(m.lower()):
                caps[m].add(pth)
    return caps

@st.cache_data(ttl=60)
def get_caps_for(base_url: str) -> Dict[str, set]:
    return build_caps(fetch_openapi(base_url))

def supports(base_url: str, method: str, path: str) -> bool:
    caps = get_caps_for(base_url)
    method = method.upper()
    if method not in caps:
        return False
    wanted = "/" + path.strip("/")
    if wanted in caps[method]:
        return True
    for tpl in caps[method]:
        if "{" in tpl and "}" in tpl and _path_to_regex(tpl).match(wanted):
            return True
    return False

def features_for(base_url: str) -> Dict[str, bool]:
    return {
        "auth"     : supports(base_url, "POST", "/auth/login"),
        "auth_me"  : supports(base_url, "GET",  "/auth/me"),
        "uploads"  : supports(base_url, "POST", "/uploads") or supports(base_url, "GET", "/uploads/{category}"),
        "plugins"  : supports(base_url, "GET",  "/plugins") and supports(base_url, "POST", "/plugins/{name}/{task}"),
        "inference": supports(base_url, "POST", "/inference"),
        "workflows": supports(base_url, "GET",  "/workflows") or supports(base_url, "POST", "/workflows/run"),
        "root"     : supports(base_url, "GET",  "/") or supports(base_url, "GET", "/docs") or supports(base_url, "GET", "/redoc"),
    }
