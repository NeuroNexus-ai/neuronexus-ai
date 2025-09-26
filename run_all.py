#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NeuroNexus-ai — Pure ANSI Pro Launcher (no external dependencies).

Features
--------
- Strong colored UI (ANSI + optional Windows enable)
- CLI options: open/no-open, prefer lan/local, no-clipboard, no-beep, port-bump
- Per-service log files in ``logs/<name>.log``
- Optional clipboard copy of LAN URL (Windows ctypes)
- Auto port bump if the port is in use (up to N)
- Health spinner and timing

Notes
-----
All code strings and documentation are provided in English to comply with the
project standards. This module focuses on formatting and documentation only;
no behavior changes were intentionally introduced.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
SERVERS_JSON = ROOT / "servers.json"
LOG_DIR = ROOT / "logs"


# ── Config (CLI) ───────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the launcher.

    Returns:
        argparse.Namespace: The parsed arguments including:
            - no_open (bool): Do not open the browser automatically.
            - prefer (str): Preferred UI URL to open: "lan" or "local".
            - no_clipboard (bool): Do not copy the URL to the clipboard on
              Windows.
            - no_beep (bool): Do not emit a success beep after startup.
            - port_bump (int): Number of attempts to increase the port if it is
              already in use.
    """

    parser = argparse.ArgumentParser(
        prog="run_all", description="NeuroNexus-ai — Pure ANSI Pro Launcher"
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not open the browser automatically.",
    )
    parser.add_argument(
        "--prefer",
        choices=["lan", "local"],
        default="lan",
        help="Open the preferred interface URL (lan or local).",
    )
    parser.add_argument(
        "--no-clipboard",
        action="store_true",
        help="Do not copy the URL to the clipboard (Windows only).",
    )
    parser.add_argument(
        "--no-beep",
        action="store_true",
        help="Do not emit a success beep after startup.",
    )
    parser.add_argument(
        "--port-bump",
        type=int,
        default=20,
        help=(
            "Number of attempts to increase the port if it is already in use."
        ),
    )
    return parser.parse_args()


ARGS = parse_args()
OPEN_BROWSER = not ARGS.no_open
COPY_CLIPBOARD = not ARGS.no_clipboard
PORT_BUMP_STEPS = ARGS.port_bump
PREFER_TARGET = (ARGS.prefer or "lan").lower()  # "lan" or "local"


# ── ANSI Colors ────────────────────────────────────────────────────────────────
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
FG_RED = "\033[31m"
FG_GREEN = "\033[32m"
FG_YELLOW = "\033[33m"
FG_BLUE = "\033[34m"
FG_MAGENTA = "\033[35m"
FG_CYAN = "\033[36m"
FG_WHITE = "\033[37m"


def c(txt: str, *styles: str) -> str:
    """Wrap text in ANSI style sequences.

    Args:
        txt (str): The input text to style.
        *styles (str): ANSI style codes to prepend to the text.

    Returns:
        str: Styled text with a trailing reset code.
    """

    return "".join(styles) + txt + RESET


# ── Enable ANSI on Windows consoles ────────────────────────────────────────────

def _enable_ansi_on_windows() -> None:
    """Enable ANSI escape sequence handling on Windows consoles.

    On non-Windows platforms this is a no-op. Errors are silently ignored to
    avoid impacting the user experience.
    """

    if os.name != "nt":
        return
    try:
        import ctypes  # Standard library only.

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            enable_virtual_terminal_processing = 0x0004
            kernel32.SetConsoleMode(
                handle, mode.value | enable_virtual_terminal_processing
            )
    except Exception:
        # Best-effort: ignore failures.
        pass


_enable_ansi_on_windows()


# ── Clipboard (Windows only, no deps) ─────────────────────────────────────────

def copy_to_clipboard(text: str) -> None:
    """Copy the given text to the Windows clipboard.

    This function is a no-op on non-Windows platforms or when clipboard copying
    is disabled via CLI.

    Args:
        text (str): The text to copy to the clipboard.
    """

    if os.name != "nt" or not COPY_CLIPBOARD:
        return
    try:
        import ctypes
        import ctypes.wintypes as wt  # noqa: F401  # Type aliases may be used.

        gmem_moveable = 0x0002
        cf_unicodetext = 13
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        user32.OpenClipboard(0)
        user32.EmptyClipboard()
        data = ctypes.create_unicode_buffer(text)
        handle = kernel32.GlobalAlloc(gmem_moveable, (len(text) + 1) * 2)
        ptr = kernel32.GlobalLock(handle)
        ctypes.memmove(ptr, ctypes.addressof(data), (len(text) + 1) * 2)
        kernel32.GlobalUnlock(handle)
        user32.SetClipboardData(cf_unicodetext, handle)
        user32.CloseClipboard()
    except Exception:
        # Best-effort: ignore failures.
        pass


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_port(cmd: List[str]) -> Optional[int]:
    """Extract the port value from a command list if present.

    Args:
        cmd (List[str]): The command-line list, e.g. ["--port", "8501"].

    Returns:
        Optional[int]: The parsed port number if found and valid, otherwise
        ``None``.
    """

    for flag in ("--port", "--server.port"):
        if flag in cmd:
            idx = cmd.index(flag)
            if idx + 1 < len(cmd):
                try:
                    return int(cmd[idx + 1])
                except Exception:
                    return None
    return None


def _replace_port_in_cmd(cmd: List[str], new_port: int) -> List[str]:
    """Replace the port value in a command list with a new port.

    Args:
        cmd (List[str]): The original command list.
        new_port (int): The new port to set.

    Returns:
        List[str]: A copy of the command list with the updated port value where
        applicable.
    """

    out = cmd[:]
    for flag in ("--port", "--server.port"):
        if flag in out:
            idx = out.index(flag)
            if idx + 1 < len(out):
                out[idx + 1] = str(new_port)
    return out


def _pick_local_url(svc: Dict[str, Any]) -> Optional[str]:
    """Pick the local URL (localhost/127.0.0.1) from a service definition.

    Args:
        svc (Dict[str, Any]): The service configuration.

    Returns:
        Optional[str]: A matching local URL if found, else ``None``.
    """

    for url in svc.get("health", []):
        if "127.0.0.1" in url or "localhost" in url:
            return url
    return None


def _lan_ip() -> Optional[str]:
    """Determine the local LAN IPv4 address using a UDP socket trick.

    Returns:
        Optional[str]: The detected LAN IP or ``None`` if detection fails.
    """

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip_addr = sock.getsockname()[0]
        sock.close()
        return ip_addr
    except Exception:
        return None


def _pick_lan_url(port: Optional[int]) -> Optional[str]:
    """Build a LAN URL using the discovered LAN IP and given port.

    Args:
        port (Optional[int]): The port to include in the URL.

    Returns:
        Optional[str]: The full LAN URL if both IP and port are available.
    """

    ip_addr = _lan_ip()
    return f"http://{ip_addr}:{port}" if (ip_addr and port) else None


def _url_ok(url: str, timeout: float = 1.5) -> bool:
    """Check if an HTTP URL responds with a 2xx status within a timeout.

    Args:
        url (str): The URL to check.
        timeout (float): Timeout in seconds for the request.

    Returns:
        bool: ``True`` if the URL returns a 2xx status code, else ``False``.
    """

    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def _port_in_use(port: int, host: str = "0.0.0.0") -> bool:
    """Determine if a TCP port is already in use on the given host.

    Args:
        port (int): The port to check.
        host (str): Host to bind for the check. Defaults to "0.0.0.0".

    Returns:
        bool: ``True`` if the port cannot be bound (in use), else ``False``.
    """

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return True
    return False


def _now() -> str:
    """Return the current time as HH:MM:SS string."""

    return time.strftime("%H:%M:%S")


def _load_services(cfg: dict) -> List[Dict[str, Any]]:
    """Load and normalize service configurations from the JSON config.

    Args:
        cfg (dict): The loaded JSON configuration.

    Returns:
        List[Dict[str, Any]]: List of service dictionaries with derived fields
        such as ``key``, ``port``, and ``local_url``.
    """

    result: List[Dict[str, Any]] = []
    for key, svc in cfg.get("services", {}).items():
        service = dict(svc)
        service["key"] = key
        service["port"] = _extract_port(service.get("cmd", []))
        service["local_url"] = _pick_local_url(service)
        result.append(service)
    return result


# ── UI ────────────────────────────────────────────────────────────────────────

def _banner(project: str) -> None:
    """Print the banner and set a Windows console title when available.

    Args:
        project (str): Project name to show in the banner and window title.
    """

    logo = r"""
 _   _                          _   _
| \ | | ___ _ __ _   _ _ __ ___| \ | | _____  __ ___  ___
|  \| |/ _ \ '__| | | | '__/ _ \  \| |/ _ \ \/ / _ \/ __|
| |\  |  __/ |  | |_| | | |  __/ |\  |  __/>  <  __/\__ \
|_| \_|\___|_|   \__,_|_|  \___|_| \_|\___/_/\_\___||___|
                  NeuroNexus-ai
"""
    # Set window title on Windows.
    if os.name == "nt":
        try:
            os.system(f"title NeuroNexus-ai • {project}")
        except Exception:
            pass

    print(c(logo, FG_CYAN, BOLD))
    print(c(f"Project: {project}", FG_GREEN, BOLD))
    print(c("─" * 78, FG_BLUE))


def _info(message: str) -> None:
    """Print an informational message with timestamp and styling.

    Args:
        message (str): The message to display.
    """

    print(c(f"[{_now()}] ", DIM) + c("i ", FG_CYAN, BOLD) + message)


def _ok(message: str) -> None:
    """Print a success message with timestamp and styling.

    Args:
        message (str): The message to display.
    """

    print(c(f"[{_now()}] ", DIM) + c("OK ", FG_GREEN, BOLD) + message)


def _warn(message: str) -> None:
    """Print a warning message with timestamp and styling.

    Args:
        message (str): The message to display.
    """

    print(c(f"[{_now()}] ", DIM) + c("! ", FG_YELLOW, BOLD) + c(message, FG_YELLOW))


def _err(message: str) -> None:
    """Print an error message with timestamp and styling.

    Args:
        message (str): The message to display.
    """

    print(c(f"[{_now()}] ", DIM) + c("X ", FG_RED, BOLD) + message)


def _print_table(services: List[Dict[str, Any]]) -> None:
    """Render a simple text table of services and their URLs.

    Args:
        services (List[Dict[str, Any]]): Normalized service definitions.
    """

    def pad(txt: str, width: int) -> str:
        return (txt[:width] + "…") if len(txt) > width else txt + " " * (width - len(txt))

    headers = ("Service", "Port", "Local URL", "LAN URL")
    widths = (12, 6, 42, 32)
    top = (
        "┌" + "─" * widths[0] + "┬" + "─" * widths[1] + "┬" + "─" * widths[2]
        + "┬" + "─" * widths[3] + "┐"
    )
    mid = (
        "├" + "─" * widths[0] + "┼" + "─" * widths[1] + "┼" + "─" * widths[2]
        + "┼" + "─" * widths[3] + "┤"
    )
    bot = (
        "└" + "─" * widths[0] + "┴" + "─" * widths[1] + "┴" + "─" * widths[2]
        + "┴" + "─" * widths[3] + "┘"
    )

    def row(cols: List[str]) -> str:
        return (
            "│"
            + pad(cols[0], widths[0])
            + "│"
            + pad(cols[1], widths[1])
            + "│"
            + pad(cols[2], widths[2])
            + "│"
            + pad(cols[3], widths[3])
            + "│"
        )

    print(c("\nServices", FG_MAGENTA, BOLD))
    print(c(top, FG_MAGENTA))
    print(c(row([*headers]), FG_WHITE, BOLD))
    print(c(mid, FG_MAGENTA))
    for svc in services:
        port_str = str(svc.get("port") or "-")
        print(
            c(
                row(
                    [
                        svc["key"],
                        port_str,
                        svc.get("local_url") or "-",
                        svc.get("lan_url") or "-",
                    ]
                ),
                FG_MAGENTA,
            )
        )
    print(c(bot, FG_MAGENTA))


# ── Launch & Health ────────────────────────────────────────────────────────────
SPINNER = "|/-\\"


def _prepare_logs() -> None:
    """Ensure the log directory exists."""

    LOG_DIR.mkdir(parents=True, exist_ok=True)


def _open_handles(key: str) -> Tuple[Any, Any]:
    """Open a binary, unbuffered log file for the given service key.

    Args:
        key (str): The service identifier used as the log file name.

    Returns:
        Tuple[Any, Any]: A tuple of (stdout, stderr) file handles pointing to
        the same file.
    """

    _prepare_logs()
    log_file = (LOG_DIR / f"{key}.log").open("ab", buffering=0)
    return log_file, log_file  # stdout, stderr -> same file


def _start_service(svc: Dict[str, Any]) -> Tuple[Optional[subprocess.Popen], bool, int]:
    """Start a service subprocess and wait for its health endpoint.

    Args:
        svc (Dict[str, Any]): Service configuration including keys: ``key``,
            ``cwd``, ``python_exe``, ``cmd``, and health URLs.

    Returns:
        Tuple[Optional[subprocess.Popen], bool, int]: The process object (or
        ``None`` on failure), a success flag, and the final port used (or -1).
    """

    key = svc["key"]
    cwd = ROOT / svc["cwd"]
    exe = Path(svc["python_exe"])  # Python interpreter for the service.
    cmd = svc["cmd"]
    base_port = svc.get("port")
    port = base_port

    # Auto bump port if busy.
    if port and _port_in_use(port):
        bumped = False
        for step in range(1, PORT_BUMP_STEPS + 1):
            candidate = port + step
            if not _port_in_use(candidate):
                cmd = _replace_port_in_cmd(cmd, candidate)
                port = candidate
                bumped = True
                break
        if bumped:
            _warn(f"[{key}] Port {base_port} is busy -> switched to {port}")
        else:
            _err(
                f"[{key}] Port {base_port} is busy and no free port was found nearby."
            )
            return None, False, base_port

    # Update URLs with final port.
    svc["port"] = port
    svc["lan_url"] = _pick_lan_url(port)

    joined_cmd = " ".join(cmd)
    _info(f"[{key}] Starting: {exe} {joined_cmd} (cwd={cwd})")

    creation = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    out_handle, err_handle = _open_handles(key)
    proc = subprocess.Popen(
        [str(exe)] + cmd,
        cwd=str(cwd),
        stdout=out_handle,
        stderr=err_handle,
        creationflags=creation,
    )

    # Health wait with spinner.
    start = time.time()
    timeout = int(svc.get("health_timeout", 120))
    healthy = False
    for url in svc.get("health", []):
        for i in range(timeout):
            if _url_ok(url):
                print()  # End spinner line.
                _ok(f"[{key}] Healthy @ {url}")
                healthy = True
                break
            frame = SPINNER[i % len(SPINNER)]
            print(
                c(f"\r{frame} ", FG_YELLOW, BOLD)
                + c(f"waiting {key}... {i + 1}s/{timeout}s", FG_YELLOW),
                end="",
                flush=True,
            )
            time.sleep(1)
        if healthy:
            break

    if not healthy:
        print()
        _err(
            f"[{key}] Failed to become healthy within {timeout}s (see logs/{key}.log)."
        )
        try:
            proc.terminate()
        except Exception:
            pass
        return None, False, port or -1

    _info(f"[{key}] Ready in {int(time.time() - start)}s.")
    return proc, True, port or -1


# ── Open UI ────────────────────────────────────────────────────────────────────

def _open_streamlit(services: List[Dict[str, Any]]) -> None:
    """Open the Streamlit service in a browser and copy the URL if configured.

    Args:
        services (List[Dict[str, Any]]): Normalized service definitions.
    """

    for svc in services:
        if svc["key"].lower() == "streamlit":
            lan = svc.get("lan_url")
            local = svc.get("local_url")
            url = (lan or local) if PREFER_TARGET == "lan" else (local or lan)
            if url:
                _info(f"Opening Streamlit at {url}")
                if OPEN_BROWSER:
                    webbrowser.open_new_tab(url)
                copy_to_clipboard(url)
            else:
                _warn("No URL available (LAN and Local are missing).")
            return


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    """Entry point: load config, start services, and manage their lifecycle."""

    if not SERVERS_JSON.exists():
        _err(f"servers.json not found: {SERVERS_JSON}")
        sys.exit(1)
    try:
        cfg = json.loads(SERVERS_JSON.read_text(encoding="utf-8"))
    except Exception as exc:
        _err(f"Invalid servers.json: {exc}")
        sys.exit(1)

    project = cfg.get("project", "Unknown Project")
    services = _load_services(cfg)

    _banner(project)

    procs: Dict[str, subprocess.Popen] = {}
    for svc in services:
        proc, ok, _ = _start_service(svc)
        if not ok:
            _err("Aborting launch due to previous errors.")
            for p in procs.values():
                if p and p.poll() is None:
                    try:
                        p.terminate()
                    except Exception:
                        pass
            sys.exit(1)
        procs[svc["key"]] = proc  # type: ignore[assignment]

    _print_table(services)
    _open_streamlit(services)

    # Optional beep after success.
    if os.name == "nt" and not ARGS.no_beep:
        try:
            import winsound

            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            # ANSI bell fallback.
            print("\a", end="", flush=True)

    print(c("\nAll services are up. Press CTRL+C to stop.\n", FG_GREEN, BOLD))
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(c("\nStopping services...", FG_RED, BOLD))
        for p in procs.values():
            if p and p.poll() is None:
                try:
                    p.terminate()
                except Exception:
                    pass
        print(c("Bye.", FG_GREEN, BOLD))


if __name__ == "__main__":
    main()
