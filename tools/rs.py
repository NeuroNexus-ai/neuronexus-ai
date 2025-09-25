#!/usr/bin/env python3
from __future__ import annotations
import os, sys, subprocess, venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS_VENV = ROOT / ".venv.tools"
PY_EXE = TOOLS_VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
REQS = ROOT / "requirements-tools.txt"

def ensure_tools_venv() -> None:
    if not TOOLS_VENV.exists():
        print(f"[tools] creating {TOOLS_VENV} …")
        venv.EnvBuilder(with_pip=True).create(str(TOOLS_VENV))
    print("[tools] installing dev requirements …")
    subprocess.check_call([str(PY_EXE), "-m", "pip", "install", "-U", "pip"])
    subprocess.check_call([str(PY_EXE), "-m", "pip", "install", "-r", str(REQS)])

def main() -> int:
    ensure_tools_venv()
    argv = sys.argv[1:]

    # Special: bootstrap uses our cross-platform script (no JSON profiles, works everywhere)
    if argv[:1] == ["bootstrap"]:
        script = ROOT / "tools" / "bootstrap_envs.py"
        cmd = [str(PY_EXE), str(script)]
        return subprocess.call(cmd + argv[1:])  # forward any extra flags

    # Passthrough to reposmith for other commands if you still need them
    cmd = [str(PY_EXE), "-m", "reposmith_tol"] + argv
    return subprocess.call(cmd)

if __name__ == "__main__":
    raise SystemExit(main())
