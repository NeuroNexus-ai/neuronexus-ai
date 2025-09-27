# Path from repo root: fastapi\app\services\uploader_docs\__init__.py
from .service import Service
TASKS = getattr(Service, "tasks", [])
def get_tasks() -> list[str]:
    return TASKS
