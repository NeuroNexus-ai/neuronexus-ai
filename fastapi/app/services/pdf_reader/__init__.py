# Path from repo root: fastapi\app\services\dummy\__init__.py
from .service import Service

TASKS = getattr(Service, "tasks", [])

def get_tasks() -> list[str]:
    return TASKS

__all__ = ["Service", "TASKS", "get_tasks"]
