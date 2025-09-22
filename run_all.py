#!/usr/bin/env python3
from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent


# =========================
# OS / Venv helpers
# =========================
def is_windows() -> bool:
    return os.name == "nt"


def venv_python(venv_dir: Path) -> Path:
    return venv_dir / ("Scripts/python.exe" if is_windows() else "bin/python")


# =========================
# Healthcheck
# =========================
def _probe_url(url: str, timeout: float = 4.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def wait_for_any_healthy(urls: list[str], timeout_s: int = 90, interval_s: float = 1.25) -> str:
    """
    Poll a list of URLs until any returns HTTP 200.
    Returns the first healthy URL, or raises RuntimeError on timeout.
    """
    start = time.time()
    last_errors: dict[str, str] = {}
    while time.time() - start < timeout_s:
        for url in urls:
            if _probe_url(url):
                return url
            else:
                last_errors[url] = "no 200"
        time.sleep(interval_s)
    errors = ", ".join(f"{u}: {e}" for u, e in last_errors.items()) or "no response"
    raise RuntimeError(f"Healthcheck timed out after {timeout_s}s → {errors}")


# =========================
# Utilities
# =========================
def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def inherit_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")  # flush logs immediately
    if extra:
        env.update(extra)
    return env


# =========================
# API: FastAPI / Uvicorn
# =========================
def start_api() -> subprocess.Popen:
    fastapi_dir = ROOT / "fastapi"
    py = venv_python(fastapi_dir / ".venv")
    if not py.exists():
        raise FileNotFoundError(f"FastAPI venv python not found: {py}")

    use_reload = os.environ.get("RUN_ALL_RELOAD", "0").lower() in ("1", "true", "yes")

    cmd = [
        str(py), "-m", "uvicorn",
        "app.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--log-level", "debug",
    ]
    if use_reload:
        cmd.append("--reload")

    print(f"[api] Starting: {' '.join(cmd)} (cwd={fastapi_dir})")
    proc = subprocess.Popen(cmd, cwd=str(fastapi_dir), env=inherit_env())

    candidates = [
        "http://127.0.0.1:8000/health",
        "http://localhost:8000/health",
        "http://127.0.0.1:8000/docs",  # fallback if /health fails
    ]
    print(f"[api] Waiting for health @ any of: {', '.join(candidates)} (timeout 90s)")
    healthy_url = wait_for_any_healthy(candidates, timeout_s=90)
    print(f"[api] Healthy @ {healthy_url}")
    return proc


# =========================
# UI: Streamlit
# =========================
def start_streamlit() -> subprocess.Popen:
    ui_dir = ROOT / "streamlit"
    py = venv_python(ui_dir / ".venv")
    if not py.exists():
        raise FileNotFoundError(f"Streamlit venv python not found: {py}")

    cmd = [
        str(py), "-m", "streamlit", "run", "app.py",
        "--server.address", "0.0.0.0",
        "--server.port", "8501",
    ]
    print(f"[ui] Starting: {' '.join(cmd)} (cwd={ui_dir})")
    proc = subprocess.Popen(cmd, cwd=str(ui_dir), env=inherit_env())

    loopback_url = "http://127.0.0.1:8501"
    print(f"[ui] Waiting for health @ {loopback_url} (timeout 90s)")
    _ = wait_for_any_healthy([loopback_url], timeout_s=90, interval_s=1.0)
    print(f"[ui] Healthy @ {loopback_url}")

    local_ip = get_local_ip()
    local_ip_url = f"http://{local_ip}:8501"
    print(f"[ui] Access from this machine: {loopback_url}")
    print(f"[ui] Access from other devices on LAN: {local_ip_url}")

    try:
        webbrowser.open(local_ip_url)
    except Exception:
        webbrowser.open(loopback_url)

    return proc


# =========================
# Graceful Termination
# =========================
def terminate(proc: Optional[subprocess.Popen]) -> None:
    if not proc:
        return
    try:
        if is_windows():
            proc.terminate()
        else:
            proc.send_signal(signal.SIGINT)
        try:
            proc.wait(timeout=6)
        except subprocess.TimeoutExpired:
            proc.kill()
    except Exception:
        pass


# =========================
# Main
# =========================
def main() -> None:
    api_proc = ui_proc = None
    try:
        api_proc = start_api()
        ui_proc = start_streamlit()
        print("All services are up. Press CTRL+C to exit.")
        while True:
            code_api = api_proc.poll()
            code_ui = ui_proc.poll()
            if code_api is not None:
                print(f"[api] Exited with code {code_api}")
                break
            if code_ui is not None:
                print(f"[ui] Exited with code {code_ui}")
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nCTRL+C received, shutting down...")
    except Exception as e:
        print(f"\n[run_all] Fatal error: {e}", file=sys.stderr)
    finally:
        terminate(ui_proc)
        terminate(api_proc)


if __name__ == "__main__":
    main()
