#!/usr/bin/env python3
"""
Main service runner script for NeuroNexus-AI.

This script starts and monitors both the FastAPI backend and Streamlit frontend,
ensuring they are up and accessible via local and LAN URLs.
"""

from __future__ import annotations

import os
import sys
import time
import socket
import signal
import subprocess
import threading
import webbrowser
from pathlib import Path
from typing import Optional
from urllib.request import urlopen, Request

# Constants
PROJECT_NAME = "NeuroNexus-AI"
BANNER = r"""
 _   _                          _   _                     
| \ | | ___ _ __ _   _ _ __ ___| \ | | _____  __ ___  ___ 
|  \| |/ _ \ '__| | | | '__/ _ \  \| |/ _ \ \/ / _ \/ __|
| |\  |  __/ |  | |_| | | |  __/ |\  |  __/>  <  __/\__ \
|_| \_|\___|_|   \__,_|_|  \___|_| \_|\___/_/\_\___||___/
                  NeuroNexus-ai
"""
ROOT = Path(__file__).resolve().parent


class C:
    """ANSI color codes for terminal output."""
    RESET = "\033[0m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    GRAY = "\033[90m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"


def _enable_ansi_windows():
    """Enable ANSI colors on Windows terminals if possible."""
    if os.name != "nt":
        return
    try:
        import msvcrt  # noqa: F401
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            ENABLE_VTP = 0x0004
            kernel32.SetConsoleMode(handle, mode.value | ENABLE_VTP)
    except Exception:
        pass


_enable_ansi_windows()

API = {
    "name": "FastAPI",
    "workdir": ROOT / "fastapi",
    "cmd": [
        str((ROOT / "fastapi" / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))),
        "-m", "uvicorn", "app.main:app",   
        "--host", "0.0.0.0", "--port", "8000", "--log-level", "debug"
    ],
    "health_urls": [
        "http://127.0.0.1:8000/health",
        "http://localhost:8000/health",
        "http://127.0.0.1:8000/docs",
    ],
    "open_url": "http://127.0.0.1:8000/docs",
    "tag": "api",
    "color": C.CYAN,
}

UI = {
    "name": "Streamlit",
    "workdir": ROOT / "streamlit",
    "cmd": [
        str((ROOT / "streamlit" / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))),
        "-m", "streamlit", "run", "app.py",
        "--server.address", "0.0.0.0", "--server.port", "8501"
    ],
    "health_urls": [
        "http://127.0.0.1:8501/healthz",
        "http://127.0.0.1:8501",
    ],
    "open_url": "http://127.0.0.1:8501",
    "tag": "ui",
    "color": C.MAGENTA,
}

SERVICES = [API, UI]
HEALTH_TIMEOUT = 90
HEALTH_INTERVAL = 1.5


def _print_banner():
    """Print a welcome banner and project name."""
    print(f"{C.GREEN}🚀 Welcome, Tamer! PowerShell is ready with curl 8.15.0{C.RESET}\n")
    print(BANNER)
    print(f"{C.BOLD}👉 Project:{C.RESET} {PROJECT_NAME}")
    print("—" * 72)


def _lan_ip() -> str:
    """Retrieve LAN IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.2)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _wait_for_health(urls: list[str], timeout_s: int, interval_s: float) -> tuple[str, float]:
    """Check service health from a list of URLs within a timeout period."""
    start = time.perf_counter()
    last_err: Optional[Exception] = None
    while (time.perf_counter() - start) < timeout_s:
        for u in urls:
            try:
                req = Request(u, headers={"User-Agent": "curl/8.15"})
                with urlopen(req, timeout=3) as r:
                    if 200 <= r.status < 500:
                        return u, (time.perf_counter() - start)
            except Exception as e:
                last_err = e
        time.sleep(interval_s)
    raise RuntimeError(f"Healthcheck timed out. Last error: {last_err}")


def _env_with_paths(svc: dict) -> dict:
    """Return env with PYTHONPATH including service workdir and its /app."""
    env = dict(os.environ)
    extra = [
        str(svc["workdir"]),              # e.g. fastapi/
        str(Path(svc["workdir"]) / "app") # e.g. fastapi/app
    ]
    current = env.get("PYTHONPATH", "")
    parts = [p for p in (extra + (current.split(os.pathsep) if current else [])) if p]
    # dedupe while preserving order
    seen = set()
    merged = []
    for p in parts:
        if p not in seen:
            merged.append(p); seen.add(p)
    env["PYTHONPATH"] = os.pathsep.join(merged)
    return env


def _stream_output(proc: subprocess.Popen, tag: str, color: str):
    """Stream output from a subprocess with tagging and color."""
    prefix = f"{color}[{tag}]{C.RESET}"

    def _pump(stream, is_err=False):
        for line in iter(stream.readline, ""):
            text = line.rstrip()
            if not text:
                continue
            if is_err:
                print(f"{prefix} {C.YELLOW}(err){C.RESET} {text}")
            else:
                print(f"{prefix} {text}")

    if proc.stdout:
        threading.Thread(target=_pump, args=(proc.stdout, False), daemon=True).start()
    if proc.stderr:
        threading.Thread(target=_pump, args=(proc.stderr, True), daemon=True).start()


def _start_service(svc: dict) -> tuple[subprocess.Popen, str, float]:
    """Start a service subprocess and wait until it becomes healthy."""
    color = svc.get("color", C.WHITE)
    cmd_pretty = " ".join(map(str, svc["cmd"]))
    print(f"{color}[{svc['tag']}] Starting:{C.RESET} {cmd_pretty} {C.DIM}(cwd={svc['workdir']}){C.RESET}")

    env = _env_with_paths(svc)  # <<< يضيف PYTHONPATH لكل خدمة

    proc = subprocess.Popen(
        svc["cmd"],
        cwd=str(svc["workdir"]),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    )
    _stream_output(proc, svc["tag"], color)
    print(f"{color}[{svc['tag']}] Waiting for health @{C.RESET} any of: {', '.join(svc['health_urls'])} {C.DIM}(timeout {HEALTH_TIMEOUT}s){C.RESET}")
    healthy_url, elapsed = _wait_for_health(svc["health_urls"], HEALTH_TIMEOUT, HEALTH_INTERVAL)
    print(f"{color}[{svc['tag']}] {C.GREEN}Healthy{C.RESET} @ {healthy_url} {C.DIM}({elapsed:.1f}s){C.RESET}")
    return proc, healthy_url, elapsed


def _open_browser(url: str):
    """Open the default web browser at the given URL."""
    try:
        webbrowser.open(url, new=2)
    except Exception:
        pass


def _services_table(rows: list[tuple[str, str, str, str]]) -> str:
    """Format and return a table summarizing service URLs."""
    headers = ("Service", "Port", "Local URL", "LAN URL")
    cols = list(zip(*([headers] + rows)))
    widths = [max(len(str(x)) for x in col) for col in cols]

    def fmt_row(items):
        return "│ " + " │ ".join(f"{str(v):<{w}}" for v, w in zip(items, widths)) + " │"

    top = "┌" + "─" * (sum(widths) + 3 * (len(widths) - 1) + 2 * len(widths)) + "┐"
    sep = "├" + "─" * (sum(widths) + 3 * (len(widths) - 1) + 2 * len(widths)) + "┤"
    bot = "└" + "─" * (sum(widths) + 3 * (len(widths) - 1) + 2 * len(widths)) + "┘"

    lines = [top, fmt_row(headers), sep]
    for r in rows:
        lines.append(fmt_row(r))
    lines.append(bot)
    return "\n".join(lines)


def _graceful_terminate(procs: list[subprocess.Popen]):
    """Terminate all running service subprocesses gracefully."""
    print(f"{C.YELLOW}🛑 Stopping services...{C.RESET}")
    for p in procs:
        if p.poll() is None:
            try:
                if os.name == "nt":
                    os.kill(p.pid, signal.CTRL_BREAK_EVENT)
                else:
                    p.terminate()
            except Exception:
                pass
    t0 = time.time()
    while any(p.poll() is None for p in procs) and time.time() - t0 < 8:
        time.sleep(0.2)
    for p in procs:
        if p.poll() is None:
            try:
                p.kill()
            except Exception:
                pass


def main():
    """Start API and UI services and manage their lifecycle.

    Orchestrates startup of the FastAPI backend and the Streamlit UI, updates
    UI command flags to run headless and advertise the LAN address, opens a
    browser to the LAN URL once, prints an access table and boot times, and
    keeps the process alive until any child exits or the user interrupts with
    CTRL+C.
    """
    _print_banner()

    procs: list[subprocess.Popen] = []
    timings: dict[str, float] = {}

    # 1) Compute LAN IP and apply it to UI settings before starting it.
    lan = _lan_ip()
    UI["open_url"] = f"http://{lan}:8501"

    # Prevent Streamlit from opening the browser itself; advertise LAN instead
    # of 0.0.0.0.
    if "--server.headless" not in UI["cmd"]:
        UI["cmd"] += [
            "--server.headless",
            "true",
            "--browser.serverAddress",
            lan,
        ]

    try:
        # 2) Start API first.
        api_proc, _, t_api = _start_service(API)
        procs.append(api_proc)
        timings["FastAPI"] = t_api

        # 3) Start UI after adjusting its command arguments.
        ui_proc, _, t_ui = _start_service(UI)
        procs.append(ui_proc)
        timings["Streamlit"] = t_ui

        # 4) Open the browser once to the LAN URL.
        _open_browser(UI["open_url"])

        # 5) Print an access table.
        rows = [
            (
                "FastAPI",
                "8000",
                "http://127.0.0.1:8000/docs",
                f"http://{lan}:8000/docs",
            ),
            (
                "Streamlit",
                "8501",
                "http://127.0.0.1:8501",
                UI["open_url"],
            ),
        ]
        print("\n" + _services_table(rows) + "\n")
        print(
            f"{C.DIM}Boot times:{C.RESET}  FastAPI "
            f"{C.GREEN}{timings['FastAPI']:.1f}s{C.RESET}, "
            f"Streamlit {C.GREEN}{timings['Streamlit']:.1f}s{C.RESET}"
        )
        print(
            f"\n{C.GREEN}All services are up.{C.RESET} "
            f"Press {C.BOLD}CTRL+C{C.RESET} to exit."
        )
        print(
            "   • Access from this machine: "
            f"{C.BLUE}http://127.0.0.1:8501{C.RESET}"
        )
        print(
            "   • Access from other devices on LAN: "
            f"{C.BLUE}{UI['open_url']}{C.RESET}"
        )

        while all(p.poll() is None for p in procs):
            time.sleep(0.5)

    except KeyboardInterrupt:
        pass
    except Exception as e:  # bubble up message to stderr
        print(f"{C.RED}Startup failed:{C.RESET} {e}", file=sys.stderr)
    finally:
        _graceful_terminate(procs)
        print("Bye.")


if __name__ == "__main__":
    main()
