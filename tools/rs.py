#!/usr/bin/env python3
from __future__ import annotations
import os, sys, subprocess, venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV_DIR = ROOT / ".venv.tools"
PY_EXE = VENV_DIR / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
REQS = ROOT / "requirements-tools.txt"

def ensure_tools_venv() -> None:
    if not VENV_DIR.exists():
        print(f"[tools] creating {VENV_DIR} …")
        venv.EnvBuilder(with_pip=True).create(str(VENV_DIR))
    # upgrade pip & install reqs
    print("[tools] installing dev requirements …")
    subprocess.check_call([str(PY_EXE), "-m", "pip", "install", "-U", "pip"])
    subprocess.check_call([str(PY_EXE), "-m", "pip", "install", "-r", str(REQS)])

def main() -> int:
    ensure_tools_venv()
    # pass-through to reposmith_tol
    cmd = [str(PY_EXE), "-m", "reposmith_tol"] + sys.argv[1:]
    return subprocess.call(cmd)

if __name__ == "__main__":
    raise SystemExit(main())
