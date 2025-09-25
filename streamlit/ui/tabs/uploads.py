from __future__ import annotations
import streamlit as st
from core.api import api_request, show_response

def render(container, base_url: str, feats: dict) -> None:
    with container:
        st.subheader("Uploads")
        disabled = (not base_url) or (not feats.get("uploads", False))

        file = st.file_uploader("Choose a file", type=None, disabled=disabled, key="upl-file")
        if file is not None:
            files = {"file": (file.name, file.getvalue(), file.type or "application/octet-stream")}
            if st.button("POST /uploads", disabled=disabled, key="upl-post"):
                resp = api_request("POST", "/uploads", files=files)
                show_response(resp)

        st.markdown("---")
        category = st.selectbox("Category", ["pdf","image","audio","video","text","archive","docs","other"], key="upl-cat")
        if st.button(f"GET /uploads/{category}", disabled=disabled, key="upl-get"):
            resp = api_request("GET", f"/uploads/{category}")
            if resp.ok:
                data = resp.json()
                st.json(data)
                for f in data.get("files", []):
                    rel = f.get("rel_path", "")
                    fname = rel.split("/")[-1]
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"- {fname} ({f.get('size_bytes', 0)} bytes)")
                    with col2:
                        dl = api_request("GET", f"/uploads/{rel}")
                        if dl.ok:
                            st.download_button("⬇️ Download", dl.content, file_name=fname,
                                               mime=dl.headers.get("Content-Type","application/octet-stream"),
                                               key=f"dl-{rel}")
            else:
                show_response(resp)
