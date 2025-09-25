# fastapi/tools/diagram_console.py
from __future__ import annotations
import json
import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any

# ------------ locate fastapi root ------------
HERE = Path(__file__).resolve()
FASTAPI_ROOT = HERE.parents[1]  # .../fastapi
TOOLS = FASTAPI_ROOT / "tools"
GEN = TOOLS / "diagram_services_plugins.py"
OUT_DIR = FASTAPI_ROOT / "build" / "diagrams"
OUT_DIR.mkdir(parents=True, exist_ok=True)
CFG_PATH = TOOLS / ".diagram_console.json"

DEFAULTS: Dict[str, Any] = {
    "direction": "LR",
    "service": "",
    "include_empty": False,
    "edge_color": "#90A4AE",
    "edge_width": 2.0,
    "arrow_size": 2.0,
    "loader_edge_color": "#B0BEC5",
    "edge_label_color": "#455A64",
    "font": "Segoe UI",
    "font_size": 14,  # ✅ جديد
    "mermaid_font": "Segoe UI, Arial, sans-serif",
    "out": "services_plugins",
}

def load_store() -> Dict[str, Any]:
    if CFG_PATH.is_file():
        try:
            return json.loads(CFG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"last": DEFAULTS.copy(), "presets": {}}

def save_store(store: Dict[str, Any]) -> None:
    CFG_PATH.write_text(json.dumps(store, indent=2, ensure_ascii=False), encoding="utf-8")

def run_generator(cfg: Dict[str, Any]) -> int:
    args = [
        sys.executable, str(GEN),
        "--direction", cfg["direction"],
        "--edge-color", cfg["edge_color"],
        "--edge-width", str(cfg["edge_width"]),
        "--arrow-size", str(cfg["arrow_size"]),
        "--loader-edge-color", cfg["loader_edge_color"],
        "--edge-label-color", cfg["edge_label_color"],
        "--font", cfg["font"],
        "--font-size", str(cfg["font_size"]),   # ✅ ممرَّر للسكربت
        "--mermaid-font", cfg["mermaid_font"],
        "--out", cfg["out"],
    ]
    if cfg.get("service"):
        args += ["--service", cfg["service"]]
    if cfg.get("include_empty"):
        args += ["--include-empty"]

    proc = subprocess.run(args, cwd=str(FASTAPI_ROOT))
    return proc.returncode

def open_outputs(base_name: str) -> None:
    base = OUT_DIR / base_name
    opts = [base.with_suffix(".svg"), base.with_suffix(".png"), base.with_suffix(".mmd")]
    for p in opts:
        if p.exists():
            try:
                if sys.platform.startswith("win"):
                    os.startfile(p)  # type: ignore[attr-defined]
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", str(p)])
                else:
                    subprocess.Popen(["xdg-open", str(p)])
            except Exception:
                print(f"[!] Could not open: {p}")

def prompt(msg: str, default: str | None = None) -> str:
    sfx = f" [{default}]" if default is not None else ""
    val = input(f"{msg}{sfx}\n> ").strip()
    return default if (default is not None and val == "") else val

def prompt_bool(msg: str, default: bool) -> bool:
    dv = "y" if default else "n"
    val = input(f"{msg} (y/n) [{dv}]\n> ").strip().lower()
    if val == "":
        return default
    return val in ("y", "yes", "1", "true")

def prompt_float(msg: str, default: float, lo: float | None = None, hi: float | None = None) -> float:
    while True:
        val = input(f"{msg} [{default}]\n> ").strip()
        if val == "":
            return default
        try:
            f = float(val)
            if (lo is not None and f < lo) or (hi is not None and f > hi):
                print(f"Please enter between {lo} and {hi}.")
                continue
            return f
        except ValueError:
            print("Invalid number.")

def prompt_int(msg: str, default: int, lo: int | None = None, hi: int | None = None) -> int:
    while True:
        val = input(f"{msg} [{default}]\n> ").strip()
        if val == "":
            return default
        try:
            i = int(val)
            if (lo is not None and i < lo) or (hi is not None and i > hi):
                print(f"Please enter between {lo} and {hi}.")
                continue
            return i
        except ValueError:
            print("Invalid integer.")

def main():
    store = load_store()
    cfg = {**DEFAULTS, **store.get("last", {})}

    while True:
        print("\n=== Diagram Console ===")
        print(f"1) Direction          : {cfg['direction']}  (LR/TB)")
        print(f"2) Service (filter)   : {cfg['service'] or '(all)'}")
        print(f"3) Include empty      : {cfg['include_empty']}")
        print(f"4) Edge color         : {cfg['edge_color']}")
        print(f"5) Edge width         : {cfg['edge_width']}")
        print(f"6) Arrow size         : {cfg['arrow_size']}")
        print(f"7) Loader edge color  : {cfg['loader_edge_color']}")
        print(f"8) Edge label color   : {cfg['edge_label_color']}")
        print(f"9) Font (Graphviz)    : {cfg['font']}")
        print(f"c) Font size          : {cfg['font_size']}  (6–48)")   # ✅ جديد
        print(f"a) Mermaid font       : {cfg['mermaid_font']}")
        print(f"b) Output base name   : {cfg['out']}")
        print("r) Run generator")
        print("o) Open outputs (SVG/PNG/MMD)")
        print("s) Save preset")
        print("l) Load preset")
        print("d) Delete preset")
        print("q) Quit")
        sel = input("> ").strip().lower()

        if sel == "1":
            val = prompt("Direction (LR/TB)", cfg["direction"]).upper()
            cfg["direction"] = "TB" if val == "TB" else "LR"
        elif sel == "2":
            v = prompt("Service filter (empty for all)", cfg["service"])
            cfg["service"] = "" if v.lower() in ("", "(all)") else v
        elif sel == "3":
            cfg["include_empty"] = prompt_bool("Include empty services/plugins?", cfg["include_empty"])
        elif sel == "4":
            cfg["edge_color"] = prompt("Edge color (#RRGGBB)", cfg["edge_color"])
        elif sel == "5":
            cfg["edge_width"] = prompt_float("Edge width", cfg["edge_width"], 0.2, 6.0)
        elif sel == "6":
            cfg["arrow_size"] = prompt_float("Arrow size", cfg["arrow_size"], 0.2, 6.0)
        elif sel == "7":
            cfg["loader_edge_color"] = prompt("Loader edge color (#RRGGBB)", cfg["loader_edge_color"])
        elif sel == "8":
            cfg["edge_label_color"] = prompt("Edge label color (#RRGGBB)", cfg["edge_label_color"])
        elif sel == "9":
            cfg["font"] = prompt("Graphviz font family", cfg["font"])
        elif sel == "c":
            cfg["font_size"] = prompt_int("Graphviz font size", cfg["font_size"], 6, 48)
        elif sel == "a":
            cfg["mermaid_font"] = prompt("Mermaid font", cfg["mermaid_font"])
        elif sel == "b":
            cfg["out"] = prompt("Output base name (no extension)", cfg["out"])
        elif sel == "r":
            # احفظ آخر إعدادات قبل التشغيل
            store["last"] = cfg.copy()
            save_store(store)
            code = run_generator(cfg)
            print("✔ Generated successfully." if code == 0 else f"✖ Generator exited with code {code}.")
        elif sel == "o":
            open_outputs(cfg["out"])
        elif sel == "s":
            name = prompt("Preset name", "")
            if name:
                store.setdefault("presets", {})[name] = cfg.copy()
                save_store(store)
                print(f"✔ Preset '{name}' saved.")
            else:
                print("No name entered.")
        elif sel == "l":
            keys = sorted(store.get("presets", {}).keys())
            if not keys:
                print("No presets saved.")
            else:
                print("Available presets:")
                for i, k in enumerate(keys, 1):
                    print(f"  {i}) {k}")
                idx = prompt_int("Choose #", 1, 1, len(keys))
                chosen = keys[idx - 1]
                cfg = {**DEFAULTS, **store["presets"][chosen]}
                print(f"✔ Preset '{chosen}' loaded.")
        elif sel == "d":
            keys = sorted(store.get("presets", {}).keys())
            if not keys:
                print("No presets to delete.")
            else:
                print("Saved presets:")
                for i, k in enumerate(keys, 1):
                    print(f"  {i}) {k}")
                idx = prompt_int("Delete #", 1, 1, len(keys))
                removed = keys[idx - 1]
                store["presets"].pop(removed, None)
                save_store(store)
                print(f"✔ Preset '{removed}' deleted.")
        elif sel == "q":
            # احفظ آخر إعدادات عند الخروج
            store["last"] = cfg.copy()
            save_store(store)
            print("Bye.")
            break
        else:
            print("Choose a valid option.")

if __name__ == "__main__":
    main()
