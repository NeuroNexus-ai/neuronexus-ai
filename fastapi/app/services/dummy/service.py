# Path from repo root: fastapi\app\services\dummy\service.py
from __future__ import annotations
from typing import Any, Dict
from app.services.base import BaseService

# ✅ خيار إضافي: تعريف tasks أيضاً على مستوى الموديول (يفيد رسّام الـ AST)
tasks = ["ping", "echo"]

class Service(BaseService):
    name = "dummy"
    # ✅ “قائمة ثابتة” واضحة — مولّد الـ plugin يعتمدها
    tasks = ["ping", "echo"]

    def load(self) -> None:
        # خفيف وآمن
        return

    def ping(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {"ok": True, "pong": True}

    def echo(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {"ok": True, "echo": payload or {}}

# ✅ خيار إضافي: دالة صريحة تفيد رسّام الـ AST
def get_tasks() -> list[str]:
    return ["ping", "echo"]