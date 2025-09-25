from __future__ import annotations
import time, requests, streamlit as st
from typing import Optional, Dict, cast
from core.storage import load_servers_from_disk, save_servers_to_disk
from core.state import no_selection
from core.capabilities import features_for

def _test_connection(base_url: str) -> tuple[bool, float, str]:
    if not base_url:
        return (False, 0.0, "Empty URL")
    base = base_url.rstrip("/")
    start = time.perf_counter()
    try:
        for path in ("/health", "/"):
            try:
                r = requests.get(f"{base}{path}", timeout=5)
                dt = (time.perf_counter() - start) * 1000
                return (r.ok, dt, f"{path} → {r.status_code}")
            except requests.RequestException:
                continue
        dt = (time.perf_counter() - start) * 1000
        return (False, dt, "No reachable endpoint")
    except Exception as e:
        dt = (time.perf_counter() - start) * 1000
        return (False, dt, str(e))

def _save_update_server(new_name: str, new_url: str):
    if new_name.strip() and new_url.strip():
        if (st.session_state.selected_server
            and new_name != st.session_state.selected_server
            and st.session_state.selected_server in st.session_state.servers):
            st.session_state.servers.pop(st.session_state.selected_server, None)
        st.session_state.servers[new_name.strip()] = new_url.strip()
        st.session_state.selected_server = new_name.strip()
        save_servers_to_disk(st.session_state.servers)
        st.success("Saved/Updated ✅")
    else:
        st.error("Please enter a valid name and URL.")

def _delete_selected_server():
    name = st.session_state.selected_server
    if name in st.session_state.servers:
        base = st.session_state.servers.pop(name)
        token_map = cast(Dict[str, Optional[str]], st.session_state["token_by_server"])
        token_map.pop(base, None)
        st.session_state.selected_server = next(iter(st.session_state.servers)) if st.session_state.servers else ""
        save_servers_to_disk(st.session_state.servers)
        st.success(f"Deleted '{name}'")

def render_sidebar() -> None:
    with st.sidebar:
        st.markdown("## ⚙️ Settings (Server Management)")

        server_names = list(st.session_state.servers.keys())
        has_servers = len(server_names) > 0

        st.markdown('<div class="ns-card">', unsafe_allow_html=True)
        if has_servers:
            if st.session_state.selected_server not in server_names:
                st.session_state.selected_server = server_names[0]
            st.session_state.selected_server = st.selectbox(
                "Select Server", server_names,
                index=server_names.index(st.session_state.selected_server),
                key="svr-select",
            )
        else:
            st.info("No servers yet. Add one below to get started.")
            st.session_state.selected_server = ""
        st.markdown('</div>', unsafe_allow_html=True)

        default_name = st.session_state.selected_server or ""
        default_url = (
            st.session_state.servers.get(st.session_state.selected_server, "")
            if st.session_state.selected_server else ""
        )

        st.markdown('<div class="ns-card">', unsafe_allow_html=True)
        st.markdown("### ➕ Add / Update Server")
        with st.form("svr-form", clear_on_submit=False):
            colA, colB = st.columns(2)
            with colA:
                new_name = st.text_input("Display Name", value=default_name, placeholder="e.g. Local :8000",
                                         key="svr-display-name")
            with colB:
                new_url = st.text_input("Base URL", value=default_url, placeholder="http://localhost:8000",
                                        key="svr-base-url")
            c1, c2, c3, c4 = st.columns(4)
            save_clicked   = c1.form_submit_button("💾 Save / Update")
            test_clicked   = c2.form_submit_button("🧪 Test")
            del_clicked    = c3.form_submit_button("🗑️ Delete", disabled=not has_servers or not st.session_state.selected_server)
            reload_clicked = c4.form_submit_button("📥 Reload")

        if save_clicked:
            _save_update_server(new_name, new_url)

        if test_clicked:
            ok, ms, msg = _test_connection(new_url or default_url or "")
            state = "ok" if ok else "fail"
            st.markdown(
                f'<span class="ns-dot {state}"></span>'
                f'{"Reachable" if ok else "Unreachable"} '
                f'<span class="ns-latency">({ms:.0f} ms) · {msg}</span>',
                unsafe_allow_html=True,
            )

        if del_clicked:
            _delete_selected_server()

        if reload_clicked:
            st.session_state.servers = load_servers_from_disk()
            names = list(st.session_state.servers.keys())
            st.session_state.selected_server = names[0] if names else ""
            st.success("Reloaded from file.")
        st.markdown('</div>', unsafe_allow_html=True)

        # Token badge + logout
        st.markdown('<div class="ns-card">', unsafe_allow_html=True)
        if not no_selection() and st.session_state.selected_server in st.session_state.servers:
            current_base = st.session_state.servers[st.session_state.selected_server]
            token_map = cast(Dict[str, Optional[str]], st.session_state["token_by_server"])
            if token_map.get(current_base):
                st.markdown('<span class="ns-chip">🔐 Token exists for this server</span>', unsafe_allow_html=True)
                def _logout():
                    token_map[current_base] = None
                    st.success("Token cleared.")
                st.button("Logout (Delete Token)", key="svr-logout", use_container_width=True, on_click=_logout)
            else:
                st.markdown('<span class="ns-chip">🔓 No token for this server yet.</span>', unsafe_allow_html=True)
        else:
            st.caption("Select or add a server to manage tokens.")
        st.markdown('</div>', unsafe_allow_html=True)

        # Capability chips
        if not no_selection() and st.session_state.selected_server in st.session_state.servers:
            base_for_badges = st.session_state.servers[st.session_state.selected_server]
            feats = features_for(base_for_badges)
            label_map = {
                "auth":"Auth", "uploads":"Uploads", "plugins":"Plugins",
                "inference":"Inference", "workflows":"Workflows", "root":"Health/Docs"
            }
            chips = []
            for k, lbl in label_map.items():
                ok = feats.get(k, False)
                dot = '<span class="ns-dot ok"></span>' if ok else '<span class="ns-dot fail"></span>'
                chips.append(f'<span class="ns-chip">{dot}{lbl}</span>')
            st.markdown('<div class="ns-card">' + " ".join(chips) + "</div>", unsafe_allow_html=True)
