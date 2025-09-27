# Path from repo root: fastapi\app\main.py
from __future__ import annotations

import asyncio
import contextlib
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.config import get_settings
from app.core.logging_ import setup_logging
from app.core.errors import register_exception_handlers
from app.core.path_utils import as_path
from app.api.routes_auth import router as auth_router
from app.api.router_inference import router as inference_router
from app.api.router_plugins import router as plugins_router
from app.api.router_services import router as services_router
from app.api.router_uploads import router as uploads_router
from app.api.router_workflows import router as workflows_router
from app.api.routes_users import router as users_router  # فعّله إذا الملف موجود

try:
    from app.plugins.loader import list_plugins
except Exception:  # fallback
    def list_plugins():
        return {}

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1) حمّل الموديلات ثم أنشئ الجداول
    try:
        from app.db import Base, engine
        from app.models.user import (
            User, Role, UserRole,
            EmailVerificationToken, PasswordResetToken, Invite
        )
        Base.metadata.create_all(bind=engine)

        # اختياري: اطبع أسماء الجداول
        from sqlalchemy import inspect
        insp = inspect(engine)
        logger.info("[db] tables at startup: %s", insp.get_table_names())
    except Exception:
        logger.exception("Failed to create tables on startup")

    # 2) Bootstrap admin
    try:
        from app.bootstrap import create_admin_if_missing
        create_admin_if_missing()
    except Exception:
        logger.exception("Failed to bootstrap admin user")

    # 3) (اختياري) Sweeper loop
    task = None
    try:
        from app.runtime.model_pool import get_model_pool
        pool = get_model_pool()

        async def sweeper():
            while True:
                pool.sweep_idle()
                await asyncio.sleep(60)

        task = asyncio.create_task(sweeper())
    except Exception:
        logger.debug("Model pool not available; skipping sweeper loop")

    try:
        yield
    finally:
        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task


# ===== App init =====
settings = get_settings()

for name in ("STATIC_DIR", "SAMPLES_DIR", "TEMPLATES_DIR", "UPLOAD_DIR"):
    if hasattr(settings, name):
        setattr(settings, name, as_path(getattr(settings, name)))

setup_logging()
templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))

app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    swagger_ui_parameters={
        "defaultModelsExpandDepth": (1 if settings.DOCS_SHOW_SCHEMAS else -1),
        "defaultModelExpandDepth": 0,
        "docExpansion": "none",
    },
)

# Static
settings.STATIC_DIR.mkdir(parents=True, exist_ok=True)
settings.SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static",  StaticFiles(directory=str(settings.STATIC_DIR),  check_dir=False), name="static")
app.mount("/samples", StaticFiles(directory=str(settings.SAMPLES_DIR), check_dir=False), name="samples")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
)

# Request ID middleware
class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response

app.add_middleware(RequestIDMiddleware)

# Errors
register_exception_handlers(app)

# Routes
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "title": settings.APP_NAME})

@app.get("/health")
def health():
    return {"status": "ok"}

EXPOSE_ENV = (settings.ENV != "production") or settings.EXPOSE_ENV_ENDPOINT
if EXPOSE_ENV:
    @app.get("/env", include_in_schema=(settings.ENV != "production"))
    def env(x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")):
        if settings.ENV == "production":
            expected = settings.ENV_SECRET_TOKEN
            if expected and x_admin_token != expected:
                raise HTTPException(status_code=403, detail="Forbidden")
        return settings.summary()

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    p = settings.STATIC_DIR / "favicon.ico"
    return FileResponse(str(p)) if p.is_file() else Response(status_code=204)

# Include routers
app.include_router(auth_router)
app.include_router(uploads_router)
app.include_router(services_router)
app.include_router(plugins_router)
app.include_router(workflows_router)
app.include_router(inference_router)
app.include_router(users_router) 

# OpenAPI enrichment (اختياري)
def _collect_plugins_and_tasks():
    try:
        registry = list_plugins()
    except Exception as e:
        logger.warning("Could not fetch plugin list for OpenAPI: %s", e)
        return [], []
    plugin_names, tasks = [], set()
    if isinstance(registry, dict):
        plugin_names = list(registry.keys())
        for manifest in registry.values():
            if isinstance(manifest, dict):
                t = manifest.get("tasks")
                if isinstance(t, (list, tuple, set)):
                    tasks.update(t)
    elif isinstance(registry, (list, tuple, set)):
        plugin_names = list(registry)
    return sorted(set(plugin_names)), sorted(tasks)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=getattr(settings, "APP_NAME", "App"),
        version=str(getattr(settings, "VERSION", "0.1.0")),
        routes=app.routes,
    )
    try:
        components = schema.get("components", {}).get("schemas", {})
        plugin_names, all_tasks = _collect_plugins_and_tasks()
        if components and plugin_names:
            for s in components.values():
                props = s.get("properties", {})
                p = props.get("plugin")
                if isinstance(p, dict) and p.get("type") == "string":
                    p["enum"] = plugin_names
                t = props.get("task")
                if isinstance(t, dict) and t.get("type") == "string" and all_tasks:
                    t["enum"] = all_tasks
    except Exception:
        logger.exception("Failed to inject plugin/task enums into OpenAPI")
    app.openapi_schema = schema
    return app.openapi_schema

app.openapi = custom_openapi