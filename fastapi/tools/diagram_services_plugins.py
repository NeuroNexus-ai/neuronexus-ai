#!/usr/bin/env python3
"""
Generate architecture diagrams from the actual project layout.

Outputs:
  - build/diagrams/services_plugins.svg (if graphviz available)
  - build/diagrams/services_plugins.png
  - build/diagrams/services_plugins.mmd (Mermaid)

Scans:
  - fastapi/app/services/**/manifest.json + service.py
  - fastapi/app/plugins/**/manifest.json + plugin.py
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ---------- CONFIG ----------
ROOT = Path(__file__).resolve().parents[1]  # fastapi/
APP = ROOT / "app"
SERVICES_DIR = APP / "services"
PLUGINS_DIR = APP / "plugins"
OUT_DIR = ROOT / "build" / "diagrams"
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------- MODELS ----------
@dataclass
class Unit:
    """Container representing either a service or a plugin."""
    name: str
    kind: str  # "service" | "plugin"
    folder: Path
    manifest: Optional[dict]
    code_path: Optional[Path]
    tasks: List[str]


# ---------- HELPERS ----------
def load_manifest(path: Path) -> Optional[dict]:
    """Load and parse a JSON manifest file."""
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def parse_tasks_from_manifest(manifest: Optional[dict]) -> List[str]:
    """Extract task names from a manifest dictionary."""
    if not isinstance(manifest, dict):
        return []
    value = manifest.get("tasks")
    if isinstance(value, list):
        return [str(task) for task in value]
    return []


def scan_units(base: Path, kind: str) -> Dict[str, Unit]:
    """Scan a base directory for units of a specific kind."""
    items: Dict[str, Unit] = {}
    if not base.exists():
        return items

    def _skip(directory: Path) -> bool:
        """Return True if a directory should be skipped."""
        name = directory.name.lower()
        if name in {"__pycache__", ".git", ".hg", ".svn"}:
            return True
        if name.startswith(".") or name.startswith("_"):
            return True
        return False

    for child in base.iterdir():
        if not child.is_dir() or _skip(child):
            continue

        manifest = load_manifest(child / "manifest.json")
        if manifest is None:
            continue

        name = (manifest or {}).get("name") or child.name

        # Common code path conventions
        code_path: Optional[Path] = None
        for relative in ("service.py", "plugin.py", "__init__.py"):
            candidate = child / relative
            if candidate.exists():
                code_path = candidate
                break

        tasks = parse_tasks_from_manifest(manifest)
        items[name] = Unit(
            name=name,
            kind=kind,
            folder=child,
            manifest=manifest,
            code_path=code_path,
            tasks=tasks,
        )
    return items


# ---------- PIPELINE ----------
def gather() -> Tuple[Dict[str, Unit], Dict[str, Unit], List[Tuple[str, str]]]:
    """Collect services, plugins, and inferred links between them."""
    services = scan_units(SERVICES_DIR, "service")
    plugins = scan_units(PLUGINS_DIR, "plugin")

    # Build mapping plugin -> service (by equal name or manifest.folder)
    links: List[Tuple[str, str]] = []
    for plugin_name, plugin in plugins.items():
        service_name: Optional[str] = None

        if plugin_name in services:
            service_name = plugin_name
        else:
            manifest = plugin.manifest or {}
            folder = manifest.get("folder") or manifest.get("name")
            if isinstance(folder, str) and folder in services:
                service_name = folder

        if service_name:
            links.append((plugin_name, service_name))

    return services, plugins, links


# ---------- MERMAID ----------
def build_mermaid(
    services: Dict[str, Unit],
    plugins: Dict[str, Unit],
    links: List[Tuple[str, str]],
    direction: str = "TB",
) -> str:
    """Create a Mermaid flowchart representing services and plugins (styled)."""

    direction = direction if direction in {"TB", "LR", "BT", "RL"} else "TB"

    lines: List[str] = [
        f"flowchart {direction}",
        "  UI([User / Streamlit]):::core --> API[/FastAPI Router\\n/plugins/{name}/{task}//]:::core",
        "  API -->|dispatch| PLUGINS{Plugin Loader}:::core",
    ]

    # Nodes
    for plugin_name, plugin in sorted(plugins.items()):
        tasks = ", ".join(plugin.tasks) if plugin.tasks else ""
        label = f"Plugin: {plugin_name}\\n{tasks}" if tasks else f"Plugin: {plugin_name}"
        lines.append(f'  P_{plugin_name}["{label}"]:::plugin')
        lines.append(f"  PLUGINS --> P_{plugin_name}")

    for service_name, service in sorted(services.items()):
        tasks = ", ".join(service.tasks) if service.tasks else ""
        label = f"Service: {service_name}\\n{tasks}" if tasks else f"Service: {service_name}"
        lines.append(f'  S_{service_name}["{label}"]:::service')

    for plugin_name, service_name in links:
        lines.append(f"  P_{plugin_name} -->|calls| S_{service_name}")

    lines += [
        "  SINK[[Result JSON]]:::core",
        "  S_* --> SINK",
        "  SINK --> UI",
        "",
        "%% Styling",
        "classDef plugin fill:#e8f1ff,stroke:#1f6feb,stroke-width:1px,rx:6,ry:6;",
        "classDef service fill:#ffe6cc,stroke:#d95700,stroke-width:1px,rx:6,ry:6;",
        "classDef core fill:#eeeeee,stroke:#888,stroke-width:1px,rx:6,ry:6;",
    ]

    return "\n".join(lines)


# ---------- GRAPHVIZ (optional, nicer SVG) ----------
def try_graphviz_render(
    services: Dict[str, Unit],
    plugins: Dict[str, Unit],
    links: List[Tuple[str, str]],
    direction: str = "TB",
) -> Optional[Path]:
    """Render an SVG (and PNG) diagram using graphviz, if available."""
    try:
        from graphviz import Digraph
    except Exception:
        return None

    direction = direction if direction in {"TB", "LR", "BT", "RL"} else "TB"

    dot = Digraph("services_plugins", format="svg")

    # Layout & global style
    dot.attr(
        rankdir=direction,         # TB (vertical), LR (horizontal), BT, RL
        labelloc="t",
        label="NeuroNexus-AI • Services ↔ Plugins",
        fontsize="20",
    )
    dot.attr("node", shape="box", style="rounded")

    # Core components (light gray)
    dot.node("UI", "User / Streamlit", shape="oval", fillcolor="lightgray", style="filled")
    dot.node("API", "FastAPI Router\n/plugins/{name}/{task}", shape="box", fillcolor="lightgray", style="filled,rounded")
    dot.node("PL", "Plugin Loader", shape="diamond", fillcolor="lightgray", style="filled")
    dot.edges([("UI", "API"), ("API", "PL")])

    # Plugins (light blue)
    for plugin_name, plugin in sorted(plugins.items()):
        label = f"Plugin: {plugin_name}"
        if plugin.tasks:
            label += f"\nTasks: {', '.join(plugin.tasks)}"
        dot.node(f"P_{plugin_name}", label, fillcolor="lightblue", style="filled,rounded")
        dot.edge("PL", f"P_{plugin_name}")

    # Services (orange)
    for service_name, service in sorted(services.items()):
        label = f"Service: {service_name}"
        if service.tasks:
            label += f"\nTasks: {', '.join(service.tasks)}"
        dot.node(f"S_{service_name}", label, fillcolor="orange", style="filled,rounded")

    # Links (plugin -> service)
    for plugin_name, service_name in links:
        dot.edge(f"P_{plugin_name}", f"S_{service_name}", label="calls")

    # Result sink
    dot.node("SINK", "Result JSON", shape="parallelogram", fillcolor="lightgray", style="filled")
    for service_name in services.keys():
        dot.edge(f"S_{service_name}", "SINK")
    dot.edge("SINK", "UI")

    # --- Keep rows tidy: Plugins in one rank, Services in one rank ---
    if plugins:
        with dot.subgraph() as p:
            p.attr(rank="same")
            for plugin_name in plugins.keys():
                p.node(f"P_{plugin_name}")
    if services:
        with dot.subgraph() as s:
            s.attr(rank="same")
            for service_name in services.keys():
                s.node(f"S_{service_name}")

    svg_path = OUT_DIR / "services_plugins.svg"
    dot.render(svg_path.with_suffix(""), cleanup=True)

    # Also export PNG if available
    try:
        dot.format = "png"
        dot.render((OUT_DIR / "services_plugins").with_suffix(""), cleanup=True)
    except Exception:
        pass

    return svg_path


# ---------- Matplotlib fallback ----------
def matplotlib_fallback(mermaid_text: str) -> Path:
    """Render a simple block diagram with matplotlib as a fallback."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    fig, ax = plt.subplots(figsize=(8, 10), dpi=180)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 15)
    ax.axis("off")

    def box(x: float, y: float, w: float, h: float, label: str, fs: int = 11) -> None:
        rect = FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.4,rounding_size=0.2", linewidth=1.2
        )
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=fs)

    x, width, height = 1.0, 8.0, 1.6
    y = 13.0
    box(x, y, width, height, "User / Streamlit")
    y -= 2.0
    box(x, y, width, height, "FastAPI Router\n/plugins/{name}/{task}")
    y -= 2.0
    box(x, y, width, height, "Plugin Loader")
    y -= 2.0
    box(x, y, width, height, "Plugins (auto-generated wrappers)")
    y -= 2.0
    box(x, y, width, height, "Services (core logic)")
    y -= 2.0
    box(x, y, width, height, "Result JSON → Streamlit")

    png = OUT_DIR / "services_plugins.png"
    fig.savefig(png, bbox_inches="tight")
    return png


# ---------- FILTERING ----------
def filter_by_service(
    services: Dict[str, Unit],
    plugins: Dict[str, Unit],
    links: List[Tuple[str, str]],
    target_service: str,
) -> Tuple[Dict[str, Unit], Dict[str, Unit], List[Tuple[str, str]]]:
    ts = target_service.lower()

    service_key = None
    for name in services.keys():
        if name.lower() == ts:
            service_key = name
            break

    if not service_key:
        return {}, {}, []

    sel_services = {service_key: services[service_key]}
    sel_links = [(p, s) for (p, s) in links if s == service_key]
    sel_plugins = {p: plugins[p] for (p, s) in sel_links if p in plugins}

    return sel_services, sel_plugins, sel_links


# ---------- ENTRY POINT ----------
def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Generate services/plugins diagram")
    parser.add_argument(
        "--service",
        help="Render a focused diagram for a single service (by name).",
    )
    parser.add_argument(
        "--direction",
        choices=["TB", "LR", "BT", "RL"],
        default="TB",
        help="Diagram layout direction: TB (top-bottom), LR (left-right), BT (bottom-top), RL (right-left).",
    )
    args = parser.parse_args()

    services, plugins, links = gather()

    if args.service:
        s2, p2, l2 = filter_by_service(services, plugins, links, args.service)
        if not s2:
            print(f"[error] Service '{args.service}' not found. Available: {', '.join(sorted(services.keys()))}")
            return
        services, plugins, links = s2, p2, l2
        suffix = f"_{list(services.keys())[0]}"
        mmd_path = OUT_DIR / f"services_plugins{suffix}.mmd"
    else:
        mmd_path = OUT_DIR / "services_plugins.mmd"

    # Mermaid
    mermaid = build_mermaid(services, plugins, links, direction=args.direction)
    mmd_path.write_text(mermaid, encoding="utf-8")
    print(f"[ok] Mermaid saved -> {mmd_path}")

    # Graphviz (preferred)
    svg = try_graphviz_render(services, plugins, links, direction=args.direction)
    if svg:
        if args.service:
            target = list(services.keys())[0]
            new_svg = OUT_DIR / f"services_plugins_{target}.svg"
            svg.replace(new_svg)
            print(f"[ok] SVG saved -> {new_svg}")
        else:
            print(f"[ok] SVG saved -> {svg}")
    else:
        print("[warn] graphviz not available, using matplotlib fallback…")
        png = matplotlib_fallback(mermaid)
        if args.service:
            target = list(services.keys())[0]
            new_png = OUT_DIR / f"services_plugins_{target}.png"
            png.replace(new_png)
            print(f"[ok] PNG saved -> {new_png}")
        else:
            print(f"[ok] PNG saved -> {png}")


if __name__ == "__main__":
    main()
