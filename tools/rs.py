#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS_VENV = ROOT / ".venv.tools"
PY_EXE = TOOLS_VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
REQS = ROOT / "requirements-tools.txt"
SERVERS_JSON = ROOT / "servers.json"


def is_windows() -> bool:
    """Check if the current operating system is Windows."""
    return os.name == "nt"


def ensure_tools_venv() -> None:
    """Ensure the virtual environment for tools is created and dependencies are installed."""
    if not TOOLS_VENV.exists():
        print(f"[tools] creating {TOOLS_VENV} …")
        venv.EnvBuilder(with_pip=True).create(str(TOOLS_VENV))

    print("[tools] installing dev requirements …")
    subprocess.check_call([str(PY_EXE), "-m", "pip", "install", "-U", "pip"])
    subprocess.check_call([str(PY_EXE), "-m", "pip", "install", "-r", str(REQS)])


def servers_payload() -> dict:
    py_api = "fastapi/.venv/Scripts/python.exe" if is_windows() else "fastapi/.venv/bin/python"
    py_ui  = "streamlit/.venv/Scripts/python.exe" if is_windows() else "streamlit/.venv/bin/python"

    return {
        "project": "NeuroNexus-AI",
        "services": {
            "api": {
                "cwd": "fastapi",
                "python_exe": py_api,
                "cmd": [
                    "-m", "uvicorn", "app.main:app",
                    "--host", "127.0.0.1",
                    "--port", "8000",
                    "--log-level", "debug"
                ],
                "health": [
                    "http://127.0.0.1:8000/health",
                    "http://127.0.0.1:8000/docs"
                ],
                "health_timeout": 180
            },
            "streamlit": {
                "cwd": "streamlit",
                "python_exe": py_ui,
                "cmd": [
                    "-m", "streamlit", "run", "app.py",
                    "--server.address", "0.0.0.0",   # <- مهم: بدل 127.0.0.1
                    "--server.port", "8501",
                    "--server.headless", "true"
                ],
                "health": [
                    "http://127.0.0.1:8501/_stcore/health",
                    "http://127.0.0.1:8501"
                ]
            }
        }
    }



def write_servers_json(force: bool = False) -> None:
    """Write or overwrite the servers.json file."""
    if SERVERS_JSON.exists() and not force:
        print(f"[servers] exists: {SERVERS_JSON} (skip). Use --force to overwrite.")
        return

    if SERVERS_JSON.exists() and force:
        shutil.copy2(SERVERS_JSON, SERVERS_JSON.with_suffix(".json.bak"))
        print(f"[servers] backup -> {SERVERS_JSON}.bak")

    data = servers_payload()
    SERVERS_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"[servers] written -> {SERVERS_JSON}")


def main() -> int:
    """Main entry point for the script."""
    ensure_tools_venv()
    argv = sys.argv[1:]

    if argv[:1] == ["bootstrap"]:
        script = ROOT / "tools" / "bootstrap_envs.py"
        code = subprocess.call([str(PY_EXE), str(script), *argv[1:]])
        if code != 0:
            return code
        write_servers_json(force=False)
        return 0

    if argv[:1] == ["servers"]:
        force = "--force" in argv
        write_servers_json(force=force)
        return 0

    cmd = [str(PY_EXE), "-m", "reposmith_tol", *argv]
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
