# Path from repo root: fastapi\tools\generate_per_service_assets.py
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

# -----------------------------------------------------
# Constant paths (expects the file is inside fastapi/tools/)
# -----------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]  # fastapi/
SERVICES_DIR = ROOT / "app" / "services"
PLUGINS_DIR = ROOT / "app" / "plugins"
DIAG_BUILD = ROOT / "build" / "diagrams"

RECREATE = ROOT / "tools" / "recreate_plugin_wrappers.py"  # generates plugin.py + manifest.json
DIAG = ROOT / "tools" / "diagram_services_plugins.py"       # draws service/plugin diagram


# -----------------------------------------------------
# Utilities
# -----------------------------------------------------
def run(cmd: List[str]) -> None:
    """Run a command in project root and raise on failure (stdout/stderr shown on error)."""
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        msg = (
            f"\n[CMD] {' '.join(cmd)}\n"
            f"[STDOUT]\n{proc.stdout}\n"
            f"[STDERR]\n{proc.stderr}\n"
        )
        raise RuntimeError(f"Command failed: {msg}")


def discover_services() -> List[str]:
    """Discover available service names under app/services/*/service.py."""
    if not SERVICES_DIR.exists():
        return []
    return sorted([
        d.name for d in SERVICES_DIR.iterdir()
        if d.is_dir() and (d / "service.py").exists()
    ])


def ensure_dir(p: Path) -> None:
    """Ensure a directory exists."""
    p.mkdir(parents=True, exist_ok=True)


def copy_if_exists(src: Path, dst: Path) -> bool:
    """Copy a file if it exists. Returns True if copied."""
    if src.is_file():
        ensure_dir(dst.parent)
        shutil.copy2(src, dst)
        return True
    return False


# -----------------------------------------------------
# Steps
# -----------------------------------------------------
def generate_plugin(name: str, force_empty: bool = False, verbose: bool = False) -> None:
    """
    Use your tool to generate a wrapper plugin from a service:
      - app/plugins/<name>/plugin.py
      - app/plugins/<name>/manifest.json
    """
    cmd = ["python", str(RECREATE), "--only", name]
    if force_empty:
        cmd.append("--force-empty")
    if verbose:
        cmd.append("--verbose")
    run(cmd)


def draw_diagram(
    name: str,
    direction: str = "LR",
    font: str = "Segoe UI",
    font_size: int = 18,
    mermaid_font: str = "Segoe UI, Arial, sans-serif",
    include_empty: bool = False,
    out_prefix: str = "arch_",
) -> Dict[str, Path]:
    """
    Draws a diagram for the service/plugin with the same name:
      - Always generates .mmd
      - .svg and .png if Graphviz is available
    """
    out_base = f"{out_prefix}{name}"
    cmd = [
        "python", str(DIAG),
        "--service", name,
        "--direction", direction,
        "--font", font,
        "--font-size", str(font_size),
        "--mermaid-font", mermaid_font,
        "--out", out_base,
    ]
    if include_empty:
        cmd.append("--include-empty")
    run(cmd)

    return {
        "mmd": DIAG_BUILD / f"{out_base}.mmd",
        "svg": DIAG_BUILD / f"{out_base}.svg",
        "png": DIAG_BUILD / f"{out_base}.png",
    }


def update_manifest_with_diagram(name: str, diagram_dir: Path, copied: Dict[str, bool], out_prefix: str = "arch_") -> None:
    """Add 'diagram' fields to the manifest.json in the plugin with relative paths."""
    manifest = PLUGINS_DIR / name / "manifest.json"
    if not manifest.exists():
        return
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except Exception:
        data = {}

    diag_obj = data.get("diagram") or {}
    if copied.get("mmd"):
        diag_obj["mmd"] = f"{diagram_dir.name}/{out_prefix}{name}.mmd"
    if copied.get("svg"):
        diag_obj["svg"] = f"{diagram_dir.name}/{out_prefix}{name}.svg"
    if copied.get("png"):
        diag_obj["png"] = f"{diagram_dir.name}/{out_prefix}{name}.png"

    data["diagram"] = diag_obj
    manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_tasks_from_manifest(name: str) -> List[str]:
    """Read tasks from the plugin's manifest.json if available."""
    manifest = PLUGINS_DIR / name / "manifest.json"
    tasks: List[str] = []
    try:
        if manifest.is_file():
            mf = json.loads(manifest.read_text(encoding="utf-8"))
            if isinstance(mf.get("tasks"), list):
                tasks = [str(t) for t in mf["tasks"]]
    except Exception:
        pass
    return tasks


def write_readme(name: str, tasks: List[str], out_prefix: str = "arch_") -> None:
    """
    Write README.md in app/plugins/<name> describing:
      - Plugin name
      - Tasks
      - Diagram images/files
      - Example API call
    """
    plugin_dir = PLUGINS_DIR / name
    readme = plugin_dir / "README.md"
    diagram_dir = plugin_dir / "diagram"

    lines: List[str] = []
    lines.append(f"# Plugin: `{name}`\n")
    lines.append("## Tasks")
    if tasks:
        for t in tasks:
            lines.append(f"- `{t}`")
    else:
        lines.append("_No tasks discovered._")

    lines.append("\n## Diagrams")
    if diagram_dir.exists():
        imgs = []
        mmds = []
        for f in sorted(diagram_dir.iterdir()):
            if f.suffix.lower() in {".png", ".svg"}:
                rel = f.relative_to(plugin_dir).as_posix()
                imgs.append(f"![{f.stem}]({rel})")
            elif f.suffix.lower() == ".mmd":
                mmds.append(f"- Mermaid: `{f.relative_to(plugin_dir)}`")

        if imgs:
            lines.extend(imgs)
        if mmds:
            lines.extend(mmds)
        if not (imgs or mmds):
            lines.append("_No diagrams found yet._")
    else:
        lines.append("_No diagrams folder yet._")

    example_task = tasks[0] if tasks else "<task>"
    lines.append("\n## Example API Call")
    lines.append("```bash")
    lines.append(f"curl -X POST http://localhost:8000/plugins/{name}/{example_task} \\")
    lines.append("     -H 'Content-Type: application/json' \\")
    lines.append("     -d '{\"key\":\"value\"}'")
    lines.append("```")

    lines.append("\n## Example Unified Inference")
    lines.append("```bash")
    lines.append("curl -X POST http://localhost:8000/inference \\")
    lines.append("     -H 'Content-Type: application/json' \\")
    lines.append(
        f"     -d '{{\"plugin\":\"{name}\",\"task\":\"{example_task}\",\"payload\":{{\"key\":\"value\"}}}}'")
    lines.append("```")

    readme.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[OK] README.md generated for plugin: {name}")


# -----------------------------------------------------
# Orchestrator
# -----------------------------------------------------
def process_one(
    name: str,
    *,
    direction: str,
    font: str,
    font_size: int,
    mermaid_font: str,
    include_empty: bool,
    force_empty_plugin: bool,
    out_prefix: str,
    verbose: bool,
) -> None:
    """Process a single service/plugin to generate assets."""
    print(f"=== Processing: {name} ===")

    print("[1/4] generating plugin wrapper")
    generate_plugin(name, force_empty=force_empty_plugin, verbose=verbose)

    print("[2/4] drawing diagram")
    paths = draw_diagram(
        name,
        direction=direction,
        font=font,
        font_size=font_size,
        mermaid_font=mermaid_font,
        include_empty=include_empty,
        out_prefix=out_prefix,
    )

    print("[3/4] embedding diagram into plugin folder")
    target_dir = PLUGINS_DIR / name / "diagram"
    ensure_dir(target_dir)
    copied = {
        "mmd": copy_if_exists(paths["mmd"], target_dir / f"{out_prefix}{name}.mmd"),
        "svg": copy_if_exists(paths["svg"], target_dir / f"{out_prefix}{name}.svg"),
        "png": copy_if_exists(paths["png"], target_dir / f"{out_prefix}{name}.png"),
    }
    update_manifest_with_diagram(name, target_dir, copied, out_prefix=out_prefix)
    ok_files = ", ".join(k for k, v in copied.items() if v) or "none"
    print(f"[OK] copied diagram files: {ok_files}")

    print("[4/4] writing README.md")
    tasks = read_tasks_from_manifest(name)
    write_readme(name, tasks, out_prefix=out_prefix)

    print(f"=== Done: {name} ===\n")


def main() -> None:
    """Main CLI entrypoint to generate plugin assets."""
    ap = argparse.ArgumentParser(
        description="Generate per-service assets: plugin wrapper + diagram + README into each plugin folder."
    )
    ap.add_argument("--only", nargs="*", help="Specific service names to generate only")
    ap.add_argument("--direction", choices=["LR", "TB"], default="LR", help="Diagram direction")
    ap.add_argument("--font", default="Segoe UI", help="Graphviz font")
    ap.add_argument("--font-size", type=int, default=18, help="Graphviz/Mermaid font size")
    ap.add_argument("--mermaid-font", default="Segoe UI, Arial, sans-serif", help="Mermaid font")
    ap.add_argument("--include-empty", action="store_true", help="Include units with no tasks")
    ap.add_argument("--force-empty-plugin", action="store_true", help="Force plugin creation even with no tasks")
    ap.add_argument("--out-prefix", default="arch_", help="Diagram file name prefix")
    ap.add_argument("--verbose", action="store_true", help="Verbose output for wrapper tool")
    args = ap.parse_args()

    names = args.only or discover_services()
    if not names:
        print("[WARN] No services found in app/services/*")
        return

    for name in names:
        process_one(
            name,
            direction=args.direction,
            font=args.font,
            font_size=args.font_size,
            mermaid_font=args.mermaid_font,
            include_empty=args.include_empty,
            force_empty_plugin=args.force_empty_plugin,
            out_prefix=args.out_prefix,
            verbose=args.verbose,
        )


if __name__ == "__main__":
    main()

# Example usage:
#   python tools/generate_per_service_assets.py --only text-summarization image-captioning
#   python tools/generate_per_service_assets.py --include-empty --force-empty-plugin --verbose
#   python tools/generate_per_service_assets.py --direction TB --font "Arial" --font-size 16
#   python tools/generate_per_service_assets.py --out-prefix "service_"
#   python tools/generate_per_service_assets.py