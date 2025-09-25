#!/usr/bin/env python3
# tools/diagram_services_plugins.py
"""
Generate architecture diagrams (Graphviz + Mermaid) from the actual project layout.

It scans:
  - fastapi/app/services/*/service.py
  - fastapi/app/plugins/*/plugin.py

Tasks discovery (no manifest required):
  - Module-level: TASKS = ["..."] or tasks = ["..."]
  - Class-level:  class Service: tasks = ["..."]
  - Optional:     def get_tasks(): return ["...", ...]

Edges:
  - Plugin <name>  --calls-->  Service <name>  (same name)
  - Decorative nodes: Router, Plugin Loader, User/Streamlit

Outputs (under fastapi/build/diagrams):
  - services_plugins.mmd
  - services_plugins.svg  (if graphviz + dot are available)
  - services_plugins.png  (if graphviz + dot are available)

Usage examples:
  python tools/diagram_services_plugins.py --direction LR
  python tools/diagram_services_plugins.py --service whisper
  python tools/diagram_services_plugins.py --edge-color "#03A9F4" --edge-width 2 --arrow-size 1
  python tools/diagram_services_plugins.py --direction LR --font "Segoe UI" --mermaid-font "Segoe UI, Arial, sans-serif"
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------- Paths ----------
THIS = Path(__file__).resolve()
FASTAPI_ROOT = THIS.parents[1]          # .../fastapi
APP = FASTAPI_ROOT / "app"
SERVICES_DIR = APP / "services"
PLUGINS_DIR = APP / "plugins"
OUT_DIR = FASTAPI_ROOT / "build" / "diagrams"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------- Optional Graphviz ----------
try:
    import graphviz  # type: ignore
except Exception:
    graphviz = None  # type: ignore[assignment]

# ---------- Data ----------
IGNORE_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".venv", ".git", ".idea"}


@dataclass
class Unit:
    name: str
    kind: str  # "service" | "plugin"
    folder: Path
    code_path: Optional[Path]
    tasks: List[str]


# ---------- Helpers ----------
def _read_text(p: Path) -> str:
    try:
        return p.read_text("utf-8", errors="ignore")
    except Exception:
        return ""


def _extract_tasks_from_ast(tree: ast.AST) -> List[str]:
    """Find a list of strings assigned to TASKS/tasks at module or Service class level, or returned by get_tasks()."""
    tasks: List[str] = []

    def _str_list(node: ast.AST) -> Optional[List[str]]:
        if isinstance(node, (ast.List, ast.Tuple)):
            out: List[str] = []
            for elt in node.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    out.append(elt.value)
            return out
        return None

    # module-level assignments
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id in {"TASKS", "tasks"}:
                    v = _str_list(node.value)
                    if v:
                        tasks = v  # prefer module-level if present
        # class-level (Service)
        if isinstance(node, ast.ClassDef) and node.name == "Service":
            for body in node.body:
                if isinstance(body, ast.Assign):
                    for t in body.targets:
                        if isinstance(t, ast.Name) and t.id == "tasks":
                            v = _str_list(body.value)
                            if v:
                                tasks = v if not tasks else tasks  # keep module-level precedence

    # get_tasks() -> [".."]
    if not tasks:
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "get_tasks":
                for b in node.body:
                    if isinstance(b, ast.Return):
                        v = _str_list(b.value)  # type: ignore[arg-type]
                        if v:
                            tasks = v
                            break
    return tasks


def _discover_units(base: Path, kind: str) -> Dict[str, Unit]:
    """Scan folders under `base` looking for plugin.py/service.py and extract TASKS."""
    entry = "plugin.py" if kind == "plugin" else "service.py"
    units: Dict[str, Unit] = {}
    if not base.is_dir():
        return units

    for d in sorted(p for p in base.iterdir() if p.is_dir()):
        if d.name in IGNORE_DIRS or d.name.startswith("_"):
            continue

        code = d / entry
        if not code.exists():
            continue

        text = _read_text(code)
        tasks = []
        if text:
            try:
                tree = ast.parse(text)
                tasks = _extract_tasks_from_ast(tree)
            except Exception:
                tasks = []

        units[d.name] = Unit(
            name=d.name,
            kind=kind,
            folder=d,
            code_path=code if code.exists() else None,
            tasks=tasks or [],
        )
    return units


def _drop_empty(units: Dict[str, Unit]) -> Dict[str, Unit]:
    return {k: u for k, u in units.items() if u.tasks}


def _compute_links(plugins: Dict[str, Unit], services: Dict[str, Unit]) -> List[Tuple[str, str]]:
    """
    Build edges: plugin.name -> service.name (same name).
    Only include pairs that exist in both dictionaries.
    """
    links: List[Tuple[str, str]] = []
    for pname in sorted(plugins.keys()):
        if pname in services:
            links.append((pname, pname))
    return links


# ---------- Mermaid ----------
def _emit_mermaid(
    services: Dict[str, Unit],
    plugins: Dict[str, Unit],
    links: List[Tuple[str, str]],
    out_path: Path,
    direction: str,
    edge_color: str,
    edge_width: float,
    mermaid_font: str,
) -> None:
    """
    Mermaid graph with two ranks via subgraphs. Basic styling only.
    """
    dir_code = "LR" if direction.upper() == "LR" else "TB"
    lines: List[str] = []
    # Mermaid font init (themeVariables)
    lines.append(
        "%%{ init: { 'themeVariables': { 'fontFamily': '" + mermaid_font.replace("'", "\\'") + "' } } }%%"
    )
    lines.append(f"flowchart {dir_code}")

    # Subgraphs for ranks
    lines.append("  subgraph Plugins")
    for name, u in plugins.items():
        label = f"Plugin: {name}\\nTasks: {', '.join(u.tasks) if u.tasks else '-'}"
        lines.append(f'    P_{name}["{label}"]:::plugin')
    lines.append("  end")

    lines.append("  subgraph Services")
    for name, u in services.items():
        label = f"Service: {name}\\nTasks: {', '.join(u.tasks) if u.tasks else '-'}"
        lines.append(f'    S_{name}["{label}"]:::service')
    lines.append("  end")

    # Decorative nodes
    lines.append('  Router(["FastAPI Router\\n/plugins/{name}/{task}"]):::router')
    lines.append('  Loader[/"Plugin Loader"/]:::loader')
    lines.append('  User(("User / Streamlit")):::user')

    # Edges
    for p, s in links:
        lines.append(f"  P_{p} -- calls --> S_{s}")

    # Loader and router wiring (visual)
    for p in plugins.keys():
        lines.append(f"  Loader -.-> P_{p}")
    for s in services.keys():
        lines.append(f"  Loader -.-> S_{s}")
    lines.append("  Router ==> Loader")
    lines.append("  User --> Router")

    # Styles
    lines.append("  classDef plugin  fill:#b3e5fc,stroke:#0288d1,color:#0d47a1;")
    lines.append("  classDef service fill:#ffcc80,stroke:#ef6c00,color:#3e2723;")
    lines.append("  classDef router  fill:#cfd8dc,stroke:#607d8b,color:#263238;")
    lines.append("  classDef loader  fill:#eceff1,stroke:#90a4ae,color:#37474f;")
    lines.append("  classDef user    fill:#eeeeee,stroke:#9e9e9e,color:#424242;")

    # Global edge styling
    ewidth = max(1.0, float(edge_width))
    lines.append(f"  linkStyle default stroke:{edge_color},stroke-width:{ewidth}px,stroke-opacity:0.9;")

    out_path.write_text("\n".join(lines), encoding="utf-8")


# ---------- Graphviz ----------
def _emit_graphviz(
    services: Dict[str, Unit],
    plugins: Dict[str, Unit],
    links: List[Tuple[str, str]],
    out_svg: Path,
    out_png: Path,
    direction: str,
    edge_color: str,
    edge_width: float,
    arrow_size: float,
    loader_edge_color: str,
    edge_label_color: str,
    font_family: str,
) -> None:
    if graphviz is None:
        return

    dot = graphviz.Digraph(
        "services_plugins",
        filename=str(out_svg.with_suffix(".gv")),
        format="svg",
        graph_attr={
            "label": "NeuroNexus-AI • Services ↔ Plugins",
            "labelloc": "t",
            "fontsize": "18",
            "fontname": font_family,
            "rankdir": "LR" if direction.upper() == "LR" else "TB",
            "splines": "polyline",
            "concentrate": "true",
            "nodesep": "0.4",
            "ranksep": "0.7",
            "pad": "0.2",
        },
        node_attr={
            "shape": "box",
            "style": "filled,rounded",
            "fontname": font_family,
            "fontsize": "10",
        },
        edge_attr={
            "color": edge_color,
            "penwidth": str(edge_width),
            "arrowsize": str(arrow_size),
            "fontcolor": edge_label_color,
            "fontsize": "9",
            "fontname": font_family,
        },
    )

    # Clusters for ranks
    with dot.subgraph(name="cluster_plugins") as c:
        c.attr(label="")
        for name, u in plugins.items():
            label = f"Plugin: {name}\nTasks: {', '.join(u.tasks) if u.tasks else '-'}"
            c.node(
                f"P_{name}",
                label,
                fillcolor="#b3e5fc",
                color="#0288d1",
                fontcolor="#0d47a1",
            )

    with dot.subgraph(name="cluster_services") as c:
        c.attr(label="")
        for name, u in services.items():
            label = f"Service: {name}\nTasks: {', '.join(u.tasks) if u.tasks else '-'}"
            c.node(
                f"S_{name}",
                label,
                fillcolor="#ffcc80",
                color="#ef6c00",
                fontcolor="#3e2723",
            )

    # Decorative nodes
    dot.node("Router", "FastAPI Router\n/plugins/{name}/{task}",
             shape="box", fillcolor="#cfd8dc", color="#607d8b", fontcolor="#263238")
    dot.node("Loader", "Plugin Loader",
             shape="parallelogram", fillcolor="#eceff1", color="#90a4ae", fontcolor="#37474f")
    dot.node("User", "User / Streamlit",
             shape="ellipse", fillcolor="#eeeeee", color="#9e9e9e", fontcolor="#424242")

    # Core edges
    for p, s in links:
        dot.edge(f"P_{p}", f"S_{s}", label="calls")

    # Loader wiring (dashed)
    for p in plugins.keys():
        dot.edge("Loader", f"P_{p}", style="dashed", color=loader_edge_color)
    for s in services.keys():
        dot.edge("Loader", f"S_{s}", style="dashed", color=loader_edge_color)

    # Router -> Loader, User -> Router
    dot.edge("Router", "Loader", arrowhead="normal")
    dot.edge("User", "Router", arrowhead="normal")

    # Render
    try:
        dot.render(filename=str(out_svg.with_suffix("")), format="svg", cleanup=True)
    except Exception:
        pass

    # Try PNG too
    try:
        dot.render(filename=str(out_png.with_suffix("")), format="png", cleanup=True)
    except Exception:
        pass


# ---------- Main ----------
def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Services↔Plugins diagrams.")
    parser.add_argument("--direction", choices=["LR", "TB"], default="TB", help="Graph direction (LR or TB).")
    parser.add_argument("--service", default="", help="Render only a single service (and its plugin), by name.")
    parser.add_argument("--include-empty", action="store_true", help="Include units that have no tasks (debugging).")

    # Edge styling
    parser.add_argument("--edge-color", default="#90A4AE", help="Edge color (hex or name).")
    parser.add_argument("--edge-width", type=float, default=1.6, help="Edge pen width.")
    parser.add_argument("--arrow-size", type=float, default=0.8, help="Arrow head size.")
    parser.add_argument("--loader-edge-color", default="#B0BEC5", help="Edges from Plugin Loader (dashed).")
    parser.add_argument("--edge-label-color", default="#455A64", help="Edge label font color.")

    # Fonts
    parser.add_argument("--font", default="Segoe UI", help="Graphviz font family (e.g., 'Segoe UI', 'Arial').")
    parser.add_argument("--mermaid-font", default="Segoe UI, Arial, sans-serif",
                        help="Mermaid font family list (comma-separated).")

    # Output
    parser.add_argument("--out", default="services_plugins", help="Base filename (without extension).")

    args = parser.parse_args()

    services = _discover_units(SERVICES_DIR, "service")
    plugins = _discover_units(PLUGINS_DIR, "plugin")

    if not args.include_empty:
        services = _drop_empty(services)
        plugins = _drop_empty(plugins)

    # Filter single service if requested
    if args.service:
        name = args.service.strip()
        services = {k: v for k, v in services.items() if k == name}
        plugins = {k: v for k, v in plugins.items() if k == name}

    links = _compute_links(plugins, services)

    # Outputs
    base = OUT_DIR / args.out
    mmd_path = base.with_suffix(".mmd")
    svg_path = base.with_suffix(".svg")
    png_path = base.with_suffix(".png")

    _emit_mermaid(
        services,
        plugins,
        links,
        out_path=mmd_path,
        direction=args.direction,
        edge_color=args.edge_color,
        edge_width=args.edge_width,
        mermaid_font=args.mermaid_font,
    )

    _emit_graphviz(
        services,
        plugins,
        links,
        out_svg=svg_path,
        out_png=png_path,
        direction=args.direction,
        edge_color=args.edge_color,
        edge_width=args.edge_width,
        arrow_size=args.arrow_size,
        loader_edge_color=args.loader_edge_color,
        edge_label_color=args.edge_label_color,
        font_family=args.font,
    )

    print(f"[ok] Mermaid saved -> {mmd_path}")
    if graphviz is None:
        print("[warn] graphviz not installed; skipped SVG/PNG rendering")
    else:
        print(f"[ok] Graphviz SVG -> {svg_path}")
        print(f"[ok] Graphviz PNG -> {png_path}")


if __name__ == "__main__":
    sys.exit(main())
