# app/core/config.py
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict

# ------------------------------------------------------------------------------
# .env (optional) — load early so we respect any user-provided overrides
# ------------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ------------------------------------------------------------------------------
# Anchor roots (independent of CWD)
# API_ROOT points to .../fastapi, PROJECT_ROOT to .../neuronexus-ai
# ------------------------------------------------------------------------------
API_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = API_ROOT.parent

# ------------------------------------------------------------------------------
# Provide early, safe defaults for HF/Torch caches (can still be overridden by env)
# This keeps model downloads inside the repo unless the user sets APP_MODEL_CACHE_ROOT
# ------------------------------------------------------------------------------
DEFAULT_MODELS_CACHE = os.getenv("APP_MODEL_CACHE_ROOT", str(API_ROOT / "models_cache"))
os.environ.setdefault("HF_HOME", str(Path(DEFAULT_MODELS_CACHE) / "huggingface"))
os.environ.setdefault("TORCH_HOME", str(Path(DEFAULT_MODELS_CACHE) / "torch"))
Path(os.environ["HF_HOME"]).resolve().mkdir(parents=True, exist_ok=True)
Path(os.environ["TORCH_HOME"]).resolve().mkdir(parents=True, exist_ok=True)
# Quieter on Windows when symlinks are not available
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")


class Settings(BaseSettings):
    """
    Application configuration using pydantic-settings.

    - Reads from environment with prefix 'APP_' (e.g., APP_HOST, APP_PORT)
    - Also reads a .env file at project root (if present).
    - All paths are anchored to API_ROOT/PROJECT_ROOT, not CWD.
    """

    # ================================
    # Basic service configuration
    # ================================
    APP_NAME: str = "NeuroNexus-ai"
    VERSION: str = "0.2.0"
    ENV: str = Field("development", description="development | staging | production")
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True  # enable auto-reload (dev only)

    # /env endpoint exposure in production (optional)
    EXPOSE_ENV_ENDPOINT: bool = False
    ENV_SECRET_TOKEN: str | None = None  # optional token to protect /env

    # ================================
    # Logging configuration
    # ================================
    LOG_LEVEL: str = "info"                   # root console level
    LOG_LEVEL_UVICORN: str = "warning"        # uvicorn.access
    LOG_LEVEL_PLUGINS: str = "info"           # plugins file
    LOG_CONSOLE_FORMAT: str = "%(asctime)s %(levelname)s [%(name)s] %(message)s"

    LOG_ERRORS_TO_FILE: bool = True
    ERROR_LOG_FILE: Path = API_ROOT / "logs" / "errors.log"
    ERROR_LOG_MAX_BYTES: int = 1_048_576  # 1 MB
    ERROR_LOG_BACKUPS: int = 5

    LOG_PLUGINS_TO_FILE: bool = True
    PLUGINS_LOG_FILE: Path = API_ROOT / "logs" / "plugins.log"
    DOCS_SHOW_SCHEMAS: bool = False

    # ================================
    # Device / Performance
    # ================================
    DEVICE: str = Field(
        default="cuda:0",
        description="e.g., 'cuda:0', 'cpu', 'mps' (macOS), 'cuda:1', etc.",
    )
    WORKERS: int = 1  # can be used by your uvicorn launcher

    # ================================
    # Model caches (project-local by default)
    # Environment can override: APP_MODEL_CACHE_ROOT / APP_HF_HOME / APP_TORCH_HOME / APP_TRANSFORMERS_CACHE
    # ================================
    MODEL_CACHE_ROOT: Path = Path(DEFAULT_MODELS_CACHE)
    HF_HOME: Path | None = None
    TORCH_HOME: Path | None = None
    TRANSFORMERS_CACHE: Path | None = None  # usually HF_HOME/hub
    TRANSFORMERS_OFFLINE: int | bool | None = None  # 1/true to force offline

    # ================================
    # Paths (anchored to API_ROOT by default)
    # Can override with APP_STATIC_DIR, APP_TEMPLATES_DIR, APP_UPLOAD_DIR, APP_SAMPLES_DIR
    # ================================
    STATIC_DIR: Path = API_ROOT / "app" / "static"
    TEMPLATES_DIR: Path = API_ROOT / "app" / "templates"
    UPLOAD_DIR: Path = API_ROOT / "uploads"
    SAMPLES_DIR: Path = API_ROOT / "samples"
    UPLOAD_MAX_MB: int = 20

    # ================================
    # CORS configuration
    # ================================
    CORS_ALLOW_ORIGINS: list[str] = Field(default_factory=lambda: ["*"])
    CORS_ALLOW_METHODS: list[str] = Field(default_factory=lambda: ["*"])
    CORS_ALLOW_HEADERS: list[str] = Field(default_factory=lambda: ["*"])
    CORS_ALLOW_CREDENTIALS: bool = False

    # ================================
    # Database (optional)
    # ================================
    # DB_URL: str | None = None  # e.g., postgresql+psycopg://user:pass@host:5432/db
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./db/neuronexus.sqlite3",
        validation_alias=AliasChoices(
            "DATABASE_URL",                
            "APP_DATABASE_URL",            
            "APP_DATABASE_URL_SQLITE",     
            "APP_DATABASE_URL_POSTGRES",   
        ),
    )
    # ================================
    # JWT security (optional)
    # ================================
    JWT_SECRET: str | None = None
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24

    # ================================
    # Pooling / Limits
    # ================================
    MAX_ACTIVE_MODELS: int = 2  # how many heavy models can stay loaded (e.g., on GPU)
    IDLE_UNLOAD_SECONDS: int = 600  # unload a model after N seconds of inactivity
    MAX_CONCURRENCY_PER_PLUGIN: int = 2  # semaphore/queue per plugin

    # ================================
    # pydantic-settings configuration
    # ================================
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------
    # Post-init hook (Pydantic v2)
    # Compute defaults for cache dirs if not provided and make sure paths exist.
    # -------------------------------
    def model_post_init(self, __context: Any) -> None:
        if not self.MODEL_CACHE_ROOT:
            self.MODEL_CACHE_ROOT = API_ROOT / "models_cache"

        if not self.HF_HOME:
            self.HF_HOME = self.MODEL_CACHE_ROOT / "huggingface"
        if not self.TORCH_HOME:
            self.TORCH_HOME = self.MODEL_CACHE_ROOT / "torch"
        if not self.TRANSFORMERS_CACHE:
            self.TRANSFORMERS_CACHE = self.MODEL_CACHE_ROOT / "huggingface" / "hub"

        # Ensure required directories exist
        self.ensure_directories()

    # -------------------------------
    # Utilities
    # -------------------------------
    def ensure_directories(self) -> None:
        """Create required directories if they do not exist."""
        for p in [
            self.MODEL_CACHE_ROOT,
            self.HF_HOME,
            self.TORCH_HOME,
            self.TRANSFORMERS_CACHE,
            self.STATIC_DIR,
            self.TEMPLATES_DIR,
            self.UPLOAD_DIR,
            self.SAMPLES_DIR,
            self.ERROR_LOG_FILE.parent,
            self.PLUGINS_LOG_FILE.parent,
        ]:
            if p:
                Path(p).resolve().mkdir(parents=True, exist_ok=True)

    def export_env_for_caches(self) -> None:
        """
        Export environment variables for cache directories and offline mode so
        transformers / torch pick them up consistently.
        """
        os.environ.setdefault("HF_HOME", str(self.HF_HOME))
        os.environ.setdefault("TORCH_HOME", str(self.TORCH_HOME))
        # Optional: hide HF progress bars in CI
        os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")

        # Offline mode toggle
        if self.TRANSFORMERS_OFFLINE is not None:
            value = str(self.TRANSFORMERS_OFFLINE).strip().lower()
            if value in ("1", "true", "yes"):
                os.environ["TRANSFORMERS_OFFLINE"] = "1"
            else:
                os.environ.pop("TRANSFORMERS_OFFLINE", None)

    def summary(self) -> dict:
        """Small snapshot for /env or /health endpoints."""
        return {
            "app": self.APP_NAME,
            "env": self.ENV,
            "host": self.HOST,
            "port": self.PORT,
            "device": self.DEVICE,
            "workers": self.WORKERS,
            "model_cache_root": str(self.MODEL_CACHE_ROOT.resolve()),
            "hf_home": str(Path(self.HF_HOME).resolve()),
            "torch_home": str(Path(self.TORCH_HOME).resolve()),
            "transformers_cache": str(Path(self.TRANSFORMERS_CACHE).resolve()),
            "static_dir": str(self.STATIC_DIR.resolve()),
            "templates_dir": str(self.TEMPLATES_DIR.resolve()),
            "upload_dir": str(self.UPLOAD_DIR.resolve()),
            "samples_dir": str(self.SAMPLES_DIR.resolve()),
            "db_url": bool(self.DATABASE_URL),
            "jwt_enabled": bool(self.JWT_SECRET),
            "pooling": {
                "max_active_models": self.MAX_ACTIVE_MODELS,
                "idle_unload_seconds": self.IDLE_UNLOAD_SECONDS,
                "max_concurrency_per_plugin": self.MAX_CONCURRENCY_PER_PLUGIN,
            },
            "hf_offline": bool(self.TRANSFORMERS_OFFLINE),
            "logs": {
                "console": self.LOG_LEVEL,
                "errors_file": str(self.ERROR_LOG_FILE) if self.LOG_ERRORS_TO_FILE else None,
                "plugins_file": str(self.PLUGINS_LOG_FILE) if self.LOG_PLUGINS_TO_FILE else None,
            },
        }


@lru_cache
def get_settings() -> Settings:
    """
    Cached singleton pattern to load application settings once.
    IMPORTANT: Calling this early ensures cache env vars are exported
    before any heavy libraries (transformers/torch) are imported.
    """
    s = Settings()
    s.export_env_for_caches()
    return s
