# Path from repo root: fastapi\app\services\base.py
from __future__ import annotations
from typing import Any, Dict

class BaseService:
    # Service name and supported tasks
    name: str = "base"
    tasks: list[str] = []

    def load(self) -> None:
        # Load model or resources if needed
        return

    def infer(self, payload: Dict[str, Any]) -> Any:
        raise NotImplementedError