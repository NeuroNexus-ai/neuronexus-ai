#!/usr/bin/env python3
"""
Generate architecture diagrams from the actual project layout (services & plugins).

Outputs (under fastapi/build/diagrams/):
  - <out>.mmd  (Mermaid)
  - <out>.svg  (Graphviz, if available)
  - <out>.png  (Graphviz, if available)

Scans:
  - app/services/**/service.py
  - app/plugins/**/plugin.py

Task discovery strategy (AST-based, manifest-free):
  1) Module-level `TASKS = ["..."]` or `tasks = ["..."]`
  2) Class `Service`/`Plugin` attribute `tasks = [...]`
  3) Function `get_tasks()` that returns a literal list of strings

CLI examples (Windows / PowerShell):
  $env:GRAPHVIZ_DOT = "C:\\Program Files\\Graphviz\\bin\\dot.exe"  # if needed
  .\.venv\Scripts\Activate.ps1
  py tools\diagram_services_plugins.py --direction LR --font "Segoe UI" \
     --font-size 18 --mermaid-font "Segoe UI, Arial, sans-serif" --out services_plugins

Author: ChatGPT (patched for font-size + small QoL)
"""
from __future__ import annotations

import argparse
import ast
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

# ----------------------- CONFIG -----------------------
THIS_FILE = Path(__file__).resolve()
FASTAPI_ROOT = THIS_FILE.parents[1]  # .../fastapi
APP_DIR = FASTAPI_ROOT / "app"
SERVICES_DIR = APP_DIR / "services"
PLUGINS_DIR = APP_DIR / "plugins"
OUT_DIR = FASTAPI_ROOT / "build" / "diagrams"
OUT_DIR.mkdir(parents=True, exist_ok=True)

IGNORE_DIRS = {
    "__pycache__",
    ".venv",
    ".mypy_cache",
    ".ruff_cache",
    "build",
    "dist",
    "node_modules",
}

# Mermaid colors (themeVariables are set via init block)
COLOR_PLUGIN = "#90CAF9"    # light blue
COLOR_SERVICE = "#FFCC80"   # light orange
COLOR_ROUTER = "#B39DDB"    # purple-ish
COLOR_LOADER = "#B0BEC5"    # blue-grey

# Graphviz node fill colors
GV_PLUGIN = "#90CAF9"
GV_SERVICE = "#FFCC80"
GV_ROUTER = "#B39DDB"
GV_LOADER = "#B0BEC5"


# ----------------------- MODELS -----------------------
@dataclass
class Unit:
    name: str
    kind: str  # "service" | "plugin"
    folder: Path
    code_path: Optional[Path]
    tasks: List[str]


# ------------------- AST UTILITIES --------------------
def _literal_list_of_strs(node: ast.AST) -> Optional[List[str]]:
    """Return list[str] if node is a literal list/tuple of strings, else None."""
    if isinstance(node, (ast.List, ast.Tuple)):
        out: List[str] = []
        for elt in node.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                out.append(elt.value)
            else:
                return None
        return out
    return None


def _extract_tasks_from_assign(node: ast.Assign) -> Optional[List[str]]:
    # looking for assignments to names: TASKS or tasks
    for target in node.targets:
        if isinstance(target, ast.Name) and target.id.lower() == "tasks":
            return _literal_list_of_strs(node.value)
    return None


def _extract_tasks_from_class(classdef: ast.ClassDef) -> Optional[List[str]]:
    # attributes like: tasks = ["..."] inside class body
    for stmt in classdef.body:
        if isinstance(stmt, ast.Assign):
            val = _extract_tasks_from_assign(stmt)
            if val:
                return val
    return None


def _extract_tasks_from_function(funcdef: ast.FunctionDef) -> Optional[List[str]]:
    # Expecting def get_tasks(): return ["..."]
    if funcdef.name != "get_tasks":
        return None
    for stmt in funcdef.body:
        if isinstance(stmt, ast.Return):
            return _literal_list_of_strs(stmt.value)
    return None


def extract_tasks_from_file(py_path: Path) -> List[str]:
    """Parse a Python file and try to extract a list of task names.
    Order of precedence: module-level -> class attr -> get_tasks().
    """
    try:
        src = py_path.read_text(encoding="utf-8")
    except Exception:
        return []

    try:
        tree = ast.parse(src)
    except Exception:
        return []

    # 1) module-level TASKS/tasks
    for node in tree.body:
        if isinstance(node, ast.Assign):
            tasks = _extract_tasks_from_assign(node)
            if tasks:
                return tasks

    # 2) class `Service`/`Plugin` with attribute tasks
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name in {"Service", "Plugin"}:
            tasks = _extract_tasks_from_class(node)
            if tasks:
                return tasks

    # 3) def get_tasks(): return [..]
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            tasks = _extract_tasks_from_function(node)
            if tasks:
                return tasks

    return []


# ------------------- SCANNERS -------------------------
def _iter_unit_dirs(base: Path) -> Iterable[Path]:
    if not base.is_dir():
        return []
    for child in sorted(base.iterdir()):
        if not child.is_dir():
            continue
        if child.name in IGNORE_DIRS:
            continue
        yield child


def scan_units(kind: str, base_dir: Path, code_filename: str) -> Dict[str, Unit]:
    out: Dict[str, Unit] = {}
    for folder in _iter_unit_dirs(base_dir):
        name = folder.name
        py_path = folder / code_filename
        tasks: List[str] = []
        if py_path.is_file():
            tasks = extract_tasks_from_file(py_path)
        out[name] = Unit(name=name, kind=kind, folder=folder, code_path=py_path if py_path.exists() else None, tasks=tasks)
    return out


# ----------------- MERMAID GENERATOR ------------------
def write_mermaid(
    plugins: Dict[str, Unit],
    services: Dict[str, Unit],
    out_path: Path,
    *,
    direction: str = "LR",
    edge_color: str = "#90A4AE",
    edge_width: float = 2.0,
    loader_edge_color: str = "#B0BEC5",
    edge_label_color: str = "#455A64",
    font_family: str = "Segoe UI, Arial, sans-serif",
    font_size: int = 14,
) -> None:
    lines: List[str] = []

    # Theme init - set fonts
    lines.append(
        f"%%{{init: {{'themeVariables': {{ 'fontFamily': '{font_family}', 'fontSize': '{font_size}px' }} }} }}%%"
    )

    lines.append("flowchart LR" if direction == "LR" else "flowchart TB")
    lines.append(f"classDef PL fill:{COLOR_PLUGIN},stroke:#424242,stroke-width:1px")
    lines.append(f"classDef SV fill:{COLOR_SERVICE},stroke:#424242,stroke-width:1px")
    lines.append(f"classDef DEC fill:#ECEFF1,stroke:#90A4AE,stroke-width:1px")

    # Decorative nodes
    lines.append("U[User]")
    lines.append("R((API Router))")
    lines.append("L[(Loader)]")
    lines.append("class U,R,L DEC")

    # Subgraphs
    lines.append("subgraph Plugins")
    for name, u in plugins.items():
        label = f"{name}\\n({', '.join(u.tasks)})" if u.tasks else name
        lines.append(f"P_{name}[\"{label}\"]:::PL")
    lines.append("end")

    lines.append("subgraph Services")
    for name, u in services.items():
        label = f"{name}\\n({', '.join(u.tasks)})" if u.tasks else name
        lines.append(f"S_{name}[\"{label}\"]:::SV")
    lines.append("end")

    # Edges (decor)
    lines.append(f"U -- request --> R")
    lines.append(f"R -- dispatch --> S_{next(iter(services))}" if services else "")
    for s in services.keys():
        # services talk to loader and plugins generically
        lines.append(f"S_{s} -- load --> L")
        if plugins:
            lines.append(f"S_{s} -- uses --> P_{next(iter(plugins))}")

    # style edges via linkStyle (Mermaid limitation: index-based). Keep simple.
    # We won't micromanage all indices; the theme is mostly handled by classDefs.

    out_path.write_text("\n".join([ln for ln in lines if ln]), encoding="utf-8")


# ----------------- GRAPHVIZ GENERATOR -----------------
def try_write_graphviz(
    plugins: Dict[str, Unit],
    services: Dict[str, Unit],
    out_base: Path,
    *,
    direction: str,
    edge_color: str,
    edge_width: float,
    arrow_size: float,
    loader_edge_color: str,
    edge_label_color: str,
    font_family: str,
    font_size: int,
) -> Tuple[bool, Optional[str]]:
    try:
        import graphviz  # type: ignore
    except Exception as e:
        return False, f"graphviz import failed: {e}"

    dot = graphviz.Digraph(
        "services_plugins",
        graph_attr={
            "rankdir": direction,
            "fontname": font_family,
            "fontsize": str(font_size),
        },
        node_attr={
            "shape": "box",
            "style": "filled,rounded",
            "fontname": font_family,
            "fontsize": str(font_size),
        },
        edge_attr={
            "color": edge_color,
            "penwidth": str(edge_width),
            "arrowsize": str(arrow_size),
            "fontname": font_family,
            "fontsize": str(font_size),
        },
    )

    # Decorative nodes
    dot.node("U", "User", fillcolor=GV_ROUTER)
    dot.node("R", "API Router", shape="ellipse", fillcolor=GV_ROUTER)
    dot.node("L", "Loader", shape="cylinder", fillcolor=GV_LOADER)

    # Ranks (clusters)
    with dot.subgraph(name="cluster_plugins") as c:
        c.attr(label="Plugins", fontsize=str(font_size + 2))
        c.attr(style="rounded")
        for name, u in plugins.items():
            label = f"{name}\n({', '.join(u.tasks)})" if u.tasks else name
            c.node(f"P_{name}", label=label, fillcolor=GV_PLUGIN)

    with dot.subgraph(name="cluster_services") as c:
        c.attr(label="Services", fontsize=str(font_size + 2))
        c.attr(style="rounded")
        for name, u in services.items():
            label = f"{name}\n({', '.join(u.tasks)})" if u.tasks else name
            c.node(f"S_{name}", label=label, fillcolor=GV_SERVICE)

    # Edges
    if services:
        first_service = next(iter(services))
        dot.edge("U", "R")
        dot.edge("R", f"S_{first_service}")
    for s in services.keys():
        dot.edge(f"S_{s}", "L", color=loader_edge_color)
        if plugins:
            first_plugin = next(iter(plugins))
            dot.edge(f"S_{s}", f"P_{first_plugin}")

    # Render
    svg_path = str(out_base.with_suffix(".svg"))
    png_path = str(out_base.with_suffix(".png"))
    try:
        dot.render(filename=str(out_base), format="svg", cleanup=True)
        dot.render(filename=str(out_base), format="png", cleanup=True)
        return True, f"SVG -> {svg_path}\nPNG -> {png_path}"
    except Exception as e:
        return False, f"graphviz render error: {e}"


# ----------------------- MAIN -------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate Mermaid/Graphviz diagrams for services & plugins.")
    p.add_argument("--direction", choices=["LR", "TB"], default="LR", help="Layout direction: LR or TB.")
    p.add_argument("--service", default=None, help="Filter by a single service/plugin name (exact match).")
    p.add_argument("--include-empty", action="store_true", help="Include units with no discovered tasks.")

    p.add_argument("--edge-color", default="#90A4AE", help="Default edge color.")
    p.add_argument("--edge-width", type=float, default=2.0, help="Edge width (Graphviz).")
    p.add_argument("--arrow-size", type=float, default=2.0, help="Arrow size (Graphviz).")
    p.add_argument("--loader-edge-color", default="#B0BEC5", help="Edge color for loader edges.")
    p.add_argument("--edge-label-color", default="#455A64", help="Edge label color (unused in GV).")

    p.add_argument("--font", default="Segoe UI", help="Graphviz font family.")
    p.add_argument("--font-size", type=int, default=14, help="Base font size for Graphviz/Mermaid.")
    p.add_argument("--mermaid-font", default="Segoe UI, Arial, sans-serif", help="Mermaid font family list.")

    p.add_argument("--out", default="services_plugins", help="Output base name (no extension).")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # Scan
    plugins = scan_units("plugin", PLUGINS_DIR, "plugin.py")
    services = scan_units("service", SERVICES_DIR, "service.py")

    if args.service:
        name = args.service.strip()
        services = {k: v for k, v in services.items() if k == name}
        plugins = {k: v for k, v in plugins.items() if k == name}
        if not services and not plugins:
            print(f"[warn] Service '{name}' not found (no matching plugin/service).")

    if not args.include_empty:
        services = {k: v for k, v in services.items() if v.tasks}
        plugins = {k: v for k, v in plugins.items() if v.tasks}

    # Write Mermaid
    mmd_path = OUT_DIR / f"{args.out}.mmd"
    write_mermaid(
        plugins=plugins,
        services=services,
        out_path=mmd_path,
        direction=args.direction,
        edge_color=args.edge_color,
        edge_width=args.edge_width,
        loader_edge_color=args.loader_edge_color,
        edge_label_color=args.edge_label_color,
        font_family=args.mermaid_font,
        font_size=args.font_size,
    )
    print(f"[ok] Mermaid saved -> {mmd_path}")

    # Try Graphviz
    out_base = OUT_DIR / args.out
    ok, msg = try_write_graphviz(
        plugins=plugins,
        services=services,
        out_base=out_base,
        direction=args.direction,
        edge_color=args.edge_color,
        edge_width=args.edge_width,
        arrow_size=args.arrow_size,
        loader_edge_color=args.loader_edge_color,
        edge_label_color=args.edge_label_color,
        font_family=args.font,
        font_size=args.font_size,
    )
    if ok:
        print(f"[ok] Graphviz saved -> {out_base.with_suffix('.svg')} / {out_base.with_suffix('.png')}")
    else:
        print(f"[skip] Graphviz: {msg}")


if __name__ == "__main__":
    main()
