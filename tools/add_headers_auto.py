# tools/add_headers_auto.py
from __future__ import annotations
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# تخطّي مجلدات/ملفات غير مرغوبة
SKIP_DIRS = {
    ".git", ".idea", ".vscode",
    ".venv", ".venv.tools", "venv", "env",
    "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache",
    "build", "dist", "logs", "models_cache", "uploads", "secrets",
}
SKIP_BASENAMES = {"add_headers_auto.py", "fix_headers_now.py"}
SKIP_DUNDER_FILES = True  # لتضمين __init__.py غيّرها إلى False

# تعريف “السيرفرات” تلقائيًا (مجلد يحوي app/ أو core/ أو ui/ أو ملف app.py/requirements.txt)
SERVER_MARKERS_DIRS = ("app", "core", "ui")
SERVER_MARKERS_FILES = ("app.py", "requirements.txt", "pyproject.toml")

# إن أردت أن يكون المسار بالنسبة لجذر السيرفر بدل جذر المستودع، غيّر إلى False
USE_REPO_ROOT = True


def discover_servers(root: Path) -> list[Path]:
    servers = []
    for entry in root.iterdir():
        if not entry.is_dir() or entry.name in SKIP_DIRS or entry.name.startswith("."):
            continue
        has_dir = any((entry / d).is_dir() for d in SERVER_MARKERS_DIRS)
        has_file = any((entry / f).is_file() for f in SERVER_MARKERS_FILES)
        if has_dir or has_file:
            servers.append(entry)
    servers.sort(key=lambda p: p.name.lower())
    return servers


def read_text_safe(path: Path):
    for enc in ("utf-8", "cp1256", "latin-1"):
        try:
            return path.read_text(encoding=enc), enc
        except UnicodeDecodeError:
            continue
    print(f"⚠️  Could not decode file: {path}")
    return None, None


def write_text(path: Path, text: str, enc: str | None):
    path.write_text(text, encoding=enc or "utf-8")


def make_one_line_header(target: Path, base: Path) -> list[str]:
    try:
        rel = target.resolve().relative_to((REPO_ROOT if USE_REPO_ROOT else base).resolve())
    except ValueError:
        rel = target.name
    return [f"# Path from {'repo' if USE_REPO_ROOT else 'server'} root: {rel}", ""]


def has_one_line_header(lines: list[str]) -> bool:
    return len(lines) >= 1 and lines[0].startswith("# Path from ")


def has_old_raw_header(lines: list[str]) -> bool:
    return (
        len(lines) >= 3
        and lines[0].startswith("Current file:")
        and lines[1].startswith("Project root:")
        and lines[2].startswith("Path from root:")
    )


def has_old_commented_header(lines: list[str]) -> bool:
    return (
        len(lines) >= 3
        and lines[0].startswith("# Current file:")
        and lines[1].startswith("# Project root:")
        and lines[2].startswith("# Path from root:")
    )


def insert_after_shebang_encoding(lines: list[str], header: list[str]) -> list[str]:
    i = 0
    if i < len(lines) and lines[i].startswith("#!"):
        i += 1
        if i < len(lines) and ("coding:" in lines[i] or "encoding=" in lines[i]):
            i += 1
    else:
        if i < len(lines) and ("coding:" in lines[i] or "encoding=" in lines[i]):
            i += 1
    return lines[:i] + header + lines[i:]


def should_skip(rel: Path) -> bool:
    for part in rel.parts:
        if part in SKIP_DIRS:
            return True
    if rel.name in SKIP_BASENAMES:
        return True
    if SKIP_DUNDER_FILES and rel.name.startswith("__") and rel.name.endswith(".py"):
        return True
    return False


def process_py(py: Path, server_root: Path):
    text, enc = read_text_safe(py)
    if text is None:
        return
    lines = text.splitlines()

    # 1) إذا السطر الواحد موجود، لا شيء
    if has_one_line_header(lines):
        return

    # 2) إن وُجد هيدر قديم (معلّق أو خام) — حوّله لسطر واحد
    if has_old_commented_header(lines) or has_old_raw_header(lines):
        header = make_one_line_header(py, server_root)
        # احذف أول 3 أسطر (القديمة) + سطر فارغ إن وجد
        rest = lines[3:]
        if rest[:1] and rest[0].strip() == "":
            rest = rest[1:]
        new_lines = header + rest
        write_text(py, "\n".join(new_lines), enc)
        print(f"🔧 Replaced old header → one-line: {server_root.name}/{py.relative_to(server_root)}")
        return

    # 3) لا يوجد هيدر — أضف السطر الواحد
    header = make_one_line_header(py, server_root)
    new_lines = insert_after_shebang_encoding(lines, header)
    write_text(py, "\n".join(new_lines), enc)
    print(f"✅ Added one-line header: {server_root.name}/{py.relative_to(server_root)}")


def process_server(server: Path):
    print(f"🔍 Processing server: {server.name}")
    for py in server.rglob("*.py"):
        rel = py.relative_to(server)
        if should_skip(rel):
            continue
        process_py(py, server)


def main():
    for server in discover_servers(REPO_ROOT):
        process_server(server)


if __name__ == "__main__":
    main()
