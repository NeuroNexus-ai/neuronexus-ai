# fastapi/app/services/dummy/service.py
from __future__ import annotations
from typing import Any, Dict
from app.services.base import BaseService

class Service(BaseService):
    name = "dummy"
    tasks = ["ping"]  # <-- مهم: تعريف المهام على مستوى الصنف

    def load(self) -> None:
        # تهيئة اختيارية
        return

    def ping(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """يرجع الـ payload كما هو مع اسم المهمة (للاختبار)."""
        return {
            "ok": True,
            "task": "ping",
            "payload_received": dict(payload or {}),
        }
