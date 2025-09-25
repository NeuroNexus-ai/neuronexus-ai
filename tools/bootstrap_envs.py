#!/usr/bin/env python3
# Cross-platform bootstrap: creates venvs and installs requirements
from __future__ import annotations

import os
import sys
import subprocess
import venv
from pathlib import Path
from typing import Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]


def is_windows() -> bool:
    return os.name == "nt"


def bindir(venv_path: Path) -> Path:
    return venv_path / ("Scripts" if is_windows() else "bin")


def exe(name: str) -> str:
    return f"{name}.exe" if is_windows() else name


def run(cmd: Sequence[str], cwd: Optional[Path] = None) -> None:
    print(f"[run] {' '.join(cmd)}")
    subprocess.check_call(cmd, cwd=str(cwd) if cwd else None)


def ensure_venv(venv_path: Path) -> None:
    if not venv_path.exists():
        print(f"[venv] creating {venv_path} …")
        venv.EnvBuilder(with_pip=True).create(str(venv_path))
    else:
        print(f"[venv] exists: {venv_path}")


def venv_python(venv_path: Path) -> Path:
    py = bindir(venv_path) / exe("python")
    if not py.exists():  # fallback (rare)
        # Some environments only have "python3" symlink
        alt = bindir(venv_path) / ("python3.exe" if is_windows() else "python3")
        return alt if alt.exists() else py
    return py


def venv_pip(venv_path: Path) -> Optional[Path]:
    pip = bindir(venv_path) / exe("pip")
    if pip.exists():
        return pip
    # fallback to python -m pip if pip shim not present
    return None


def pip_install(venv_path: Path, *args: str) -> None:
    pip = venv_pip(venv_path)
    if pip is not None:
        run([str(pip), *args])
    else:
        py = venv_python(venv_path)
        run([str(py), "-m", "pip", *args])


def install_requirements(venv_path: Path, req_file: Path) -> None:
    if not req_file.exists():
        print(f"[warn] requirements file not found: {req_file}")
        return
    # Correct: upgrade pip via "install -U"
    pip_install(venv_path, "install", "-U", "pip")
    pip_install(venv_path, "install", "-r", str(req_file))


def bootstrap(
    api_dir: Path = ROOT / "fastapi",
    ui_dir: Path = ROOT / "streamlit",
    tools_venv: Path = ROOT / ".venv.tools",
    tools_requirements: Path = ROOT / "requirements-tools.txt",
    with_tools: bool = True,
) -> None:
    # --- API ---
    api_venv = api_dir / ".venv"
    ensure_venv(api_venv)
    install_requirements(api_venv, api_dir / "requirements.txt")

    # --- UI ---
    ui_venv = ui_dir / ".venv"
    ensure_venv(ui_venv)
    install_requirements(ui_venv, ui_dir / "requirements.txt")

    # --- Tools (reposmith / pre-commit / ruff ...) ---
    if with_tools:
        ensure_venv(tools_venv)
        install_requirements(tools_venv, tools_requirements)

    print("\n[ok] Bootstrap finished.")
    print("    - fastapi/.venv ready")
    print("    - streamlit/.venv ready")
    if with_tools:
        print("    - .venv.tools ready")


def main() -> int:
    # minimal CLI flags
    with_tools = "--no-tools" not in sys.argv
    try:
        bootstrap(with_tools=with_tools)
        return 0
    except subprocess.CalledProcessError as e:
        print(f"[error] command failed (exit {e.returncode})", file=sys.stderr)
        return e.returncode
    except Exception as e:  # noqa: BLE001
        print(f"[fatal] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
