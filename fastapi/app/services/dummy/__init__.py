from .service import Service

# discovery shims
TASKS = getattr(Service, "tasks", [])

def get_tasks() -> list[str]:
    return TASKS

__all__ = ["Service", "TASKS", "get_tasks"]
