# tools/recreate_plugin_wrappers.py
from __future__ import annotations

import argparse
import importlib
import json
import sys
import traceback
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SERVICES_DIR = ROOT / "app" / "services"
PLUGINS_DIR = ROOT / "app" / "plugins"

WRAPPER_TEMPLATE = """
from __future__ import annotations
import importlib
from typing import Any
from app.plugins.base import AIPlugin

class Plugin(AIPlugin):
    name = "__NAME__"
    tasks = __TASKS__
    provider = "local"
    _impl = None  # instance of app.services.__NAME__.service.Service

    def __init__(self) -> None:
        self.name = "__NAME__"
        # نثبت المهام المتولدة كقائمة قابلة للتعديل محليًا
        self.tasks = list(__TASKS__)

    def load(self) -> None:
        if self._impl is None:
            mod = importlib.import_module("app.services.__NAME__.service")
            Impl = getattr(mod, "Service", None) or getattr(mod, "Plugin", None)
            if Impl is None:
                raise ImportError("No Service/Plugin class found in service.py")
            self._impl = Impl()
            if hasattr(self._impl, "load"):
                self._impl.load()
        # لو الملف المتولد ما فيه مهام لأي سبب، حاول ورّثها من الـ Impl
        if (not self.tasks) and self._impl is not None:
            svc_tasks = getattr(self._impl, "tasks", [])
            if isinstance(svc_tasks, (list, tuple, set)):
                self.tasks = list(svc_tasks)

    def infer(self, payload: dict[str, Any]) -> Any:
        self.load()
        task = (payload or {}).get("task")
        if isinstance(task, str) and hasattr(self._impl, task):
            return getattr(self._impl, task)(payload)
        raise AttributeError(f"Unknown task: {task!r}")

    def __getattr__(self, item: str):
        self.load()
        if item in self.tasks and hasattr(self._impl, item):
            def _call(payload: dict[str, Any]):
                self.load()
                return getattr(self._impl, item)(payload)
            return _call
        raise AttributeError(item)
""".lstrip()


def discover_services() -> list[str]:
    names: list[str] = []
    if not SERVICES_DIR.exists():
        return names
    for d in SERVICES_DIR.iterdir():
        if d.is_dir() and (d / "service.py").exists():
            names.append(d.name)
    return sorted(names)


def _safe_get_tasks_from_class(ImplCls: Any) -> list[str]:
    t = getattr(ImplCls, "tasks", None)
    if isinstance(t, (list, tuple, set)):
        return [str(x) for x in t]
    return []


def _safe_get_tasks_from_instance(ImplCls: Any) -> list[str]:
    # نجرب إنشاء المثيل فقط إن لم تكن هناك حاجة إلى args
    try:
        obj = ImplCls()  # يفترض مُنشئ بدون بارامترات
    except Exception:
        return []
    t = getattr(obj, "tasks", None)
    if isinstance(t, (list, tuple, set)):
        return [str(x) for x in t]
    return []


def tasks_of(service_name: str, verbose: bool = False) -> list[str]:
    """
    يحاول الحصول على قائمة المهام من Service/Plugin:
    1) خاصية صنفية (class attr)
    2) إنشاء مثيل ثم قراءة tasks (كحلّ احتياطي آمن)
    """
    try:
        mod = importlib.import_module(f"app.services.{service_name}.service")
    except Exception as e:
        if verbose:
            sys.stderr.write(f"[IMPORT-ERROR] {service_name}: {e}\n{traceback.format_exc()}\n")
        return []

    ImplCls = getattr(mod, "Service", None) or getattr(mod, "Plugin", None)
    if ImplCls is None:
        if verbose:
            sys.stderr.write(f"[WARN] {service_name}: No class Service/Plugin in service.py\n")
        return []

    # 1) من مستوى الصنف
    t = _safe_get_tasks_from_class(ImplCls)
    if t:
        return t

    # 2) من المثيل
    t = _safe_get_tasks_from_instance(ImplCls)
    if t:
        return t

    if verbose:
        sys.stderr.write(f"[WARN] {service_name}: tasks not found on class/instance.\n")
    return []


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.replace("\r\n", "\n"), encoding="utf-8")


def recreate_one(name: str, *, force_empty: bool = False, verbose: bool = False) -> bool:
    tasks = tasks_of(name, verbose=verbose) or []
    if not tasks and not force_empty:
        # لا نولّد Plugin فاضيًا — نطبع تحذير ونرجع False
        sys.stderr.write(f"[SKIP] {name}: no tasks discovered. (use --force-empty to generate anyway)\n")
        return False

    pdir = PLUGINS_DIR / name
    p_py = pdir / "plugin.py"
    p_init = pdir / "__init__.py"
    manifest = pdir / "manifest.json"

    # امسح الملفات داخل مجلد الـ plugin فقط
    if pdir.exists():
        for f in pdir.iterdir():
            if f.is_file():
                f.unlink()
    else:
        pdir.mkdir(parents=True, exist_ok=True)

    code = WRAPPER_TEMPLATE.replace("__NAME__", name).replace("__TASKS__", repr(tasks))
    write_text(p_py, code)
    write_text(p_init, "")

    manifest_obj: dict[str, Any] = {
        "name": name,
        "kind": "plugin",
        "folder": name,
        "provider": "local",
        "code": f"app/plugins/{name}/plugin.py",
        "tasks": tasks,
        "models": [],
    }
    write_text(manifest, json.dumps(manifest_obj, ensure_ascii=False, indent=2))
    print(f"[OK] recreated wrapper: {name} (tasks={tasks or '[]'})")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Recreate plugin wrappers from services.")
    parser.add_argument("--only", nargs="*", help="أسماء خدمات محددة لتوليدها فقط", default=None)
    parser.add_argument("--force-empty", action="store_true", help="ولّد plugin حتى لو لم تُكتشف مهام")
    parser.add_argument("--verbose", action="store_true", help="طباعة تتبع وتشخيص")
    args = parser.parse_args()

    names = discover_services()
    if not names:
        print("[WARN] no services found under app/services/*")
        return

    if args.only:
        names = [n for n in names if n in set(args.only)]

    any_created = False
    for n in names:
        created = recreate_one(n, force_empty=args.force_empty, verbose=args.verbose)
        any_created = any_created or created

    if any_created:
        print("Recreation complete ✅")
    else:
        print("Nothing generated. (No tasks discovered or filtered by --only) ⚠️")


if __name__ == "__main__":
    main()
