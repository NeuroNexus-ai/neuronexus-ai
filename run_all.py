#!/usr/bin/env python3
from __future__ import annotations
import json, os, subprocess, sys, time, webbrowser, socket
from pathlib import Path
from typing import Any, Dict, List, Optional
import urllib.request

ROOT = Path(__file__).resolve().parent
SERVERS_JSON = ROOT / "servers.json"

# ───────────────────────────────
# Helpers
# ───────────────────────────────
def _load_services(cfg: dict) -> List[Dict[str, Any]]:
    services = []
    for key, svc in cfg.get("services", {}).items():
        service = dict(svc)
        service["key"] = key
        service["port"] = _extract_port(service.get("cmd", []))
        service["local_url"] = _pick_local_url(service)
        service["lan_url"] = _pick_lan_url(service)
        services.append(service)
    return services

def _extract_port(cmd: List[str]) -> Optional[int]:
    for flag in ("--port", "--server.port"):
        if flag in cmd:
            i = cmd.index(flag)
            if i + 1 < len(cmd):
                try:
                    return int(cmd[i + 1])
                except Exception:
                    pass
    return None

def _pick_local_url(svc: Dict[str, Any]) -> Optional[str]:
    for url in svc.get("health", []):
        if "127.0.0.1" in url or "localhost" in url:
            return url
    return None

def _pick_lan_url(svc: Dict[str, Any]) -> Optional[str]:
    if not svc.get("port"):
        return None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        lan_ip = s.getsockname()[0]
        s.close()
        return f"http://{lan_ip}:{svc['port']}"
    except Exception:
        return None


def _url_ok(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=1) as resp:
            return resp.status == 200
    except Exception:
        return False

# ───────────────────────────────
# Main
# ───────────────────────────────
def main() -> None:
    if not SERVERS_JSON.exists():
        print(f"[error] servers.json not found: {SERVERS_JSON}")
        sys.exit(1)

    cfg = json.loads(SERVERS_JSON.read_text(encoding="utf-8"))
    project_name = cfg.get("project", "Unknown Project")
    services = _load_services(cfg)
    procs: Dict[str, subprocess.Popen] = {}

    # Banner
    print("\n🚀 Welcome, Tamer! PowerShell is ready with curl 8.15.0\n")
    print(" _   _                          _   _")
    print("| \\ | | ___ _ __ _   _ _ __ ___| \\ | | _____  __ ___  ___")
    print("|  \\| |/ _ \\ '__| | | | '__/ _ \\  \\| |/ _ \\ \\/ / _ \\/ __|")
    print("| |\\  |  __/ |  | |_| | | |  __/ |\\  |  __/>  <  __/\\__ \\")
    print("|_| \\_|\\___|_|   \\__,_|_|  \\___|_| \\_|\\___/_/\\_\\___||___|")
    print("                  NeuroNexus-ai\n")
    print(f"👉 Project: {project_name}")
    print("———————————————————————————————————————————————————————————————————————————————")

    try:
        # شغّل كل الخدمات
        for svc in services:
            key, cwd, exe, cmd = svc["key"], ROOT / svc["cwd"], Path(svc["python_exe"]), svc["cmd"]
            print(f"[{key}] Starting: {exe} {' '.join(cmd)} (cwd={cwd})")
            procs[key] = subprocess.Popen(
                [str(exe)] + cmd,
                cwd=str(cwd),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            # health check
            healthy = False
            for url in svc.get("health", []):
                for _ in range(svc.get("health_timeout", 90)):
                    if _url_ok(url):
                        print(f"[{key}] Healthy @ {url}")
                        healthy = True
                        break
                    time.sleep(1)
                if healthy:
                    break
            if not healthy:
                print(f"[{key}] Failed to start within timeout")
                sys.exit(1)

        # جدول
        print("\n┌──────────────────────────────────────────────────────────────────────────────┐")
        print("│ Service    │ Port │ Local URL                   │ LAN URL                      │")
        print("├────────────┼──────┼─────────────────────────────┼──────────────────────────────┤")
        for svc in services:
            port = svc.get("port") or "-"
            print(
                f"│ {svc['key']:<10} │ {port:<4} │ {svc.get('local_url') or '-':<27} │ {svc.get('lan_url') or '-':<28} │"
            )
        print("└──────────────────────────────────────────────────────────────────────────────┘")

        # افتح Streamlit فقط
        for svc in services:
            if svc["key"].lower() == "streamlit":
                url = svc.get("lan_url") or svc.get("local_url")
                if url:
                    print(f"\n[open] Opening Streamlit at {url}")
                    webbrowser.open_new_tab(url)
                break

        print("\nAll services are up. Press CTRL+C to exit.\n")
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n🛑 Stopping services...")
        for proc in procs.values():
            if proc and proc.poll() is None:
                proc.terminate()
        print("Bye.")

if __name__ == "__main__":
    main()
