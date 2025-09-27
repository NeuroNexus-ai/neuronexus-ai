# Path from repo root: fastapi\app\plugins\uploader_image\plugin.py
from __future__ import annotations
import importlib
from typing import Any
from app.plugins.base import AIPlugin

class Plugin(AIPlugin):
    name = "uploader_image"
    tasks = ['upload_image']
    provider = "local"
    _impl = None  # instance of app.services.uploader_image.service.Service

    def __init__(self) -> None:
        self.name = "uploader_image"
        # نثبت المهام المتولدة كقائمة قابلة للتعديل محليًا
        self.tasks = list(['upload_image'])

    def load(self) -> None:
        if self._impl is None:
            mod = importlib.import_module("app.services.uploader_image.service")
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