# scripts/test_env_endpoint.py
import os
import sys
import importlib
from contextlib import contextmanager
from typing import Dict, Tuple, List

from starlette.testclient import TestClient  # يأتي مع Starlette/FastAPI


@contextmanager
def patched_environ(new_vars: Dict[str, str]):
    """Patch environment variables temporarily."""
    old: Dict[str, Tuple[bool, str]] = {}
    try:
        for k, v in new_vars.items():
            old[k] = (k in os.environ, os.environ.get(k, ""))
            os.environ[k] = v
        yield
    finally:
        for k, (had, val) in old.items():
            if had:
                os.environ[k] = val
            else:
                os.environ.pop(k, None)


def load_app_fresh():
    """
    Reload the app with current env to ensure Settings are re-read.
    We reload app.core.config first (to reset any lru_cache on get_settings),
    then reload app.main and return app.
    """
    if "app.core.config" in sys.modules:
        importlib.reload(sys.modules["app.core.config"])
    else:
        import app.core.config  # noqa: F401

    if "app.main" in sys.modules:
        importlib.reload(sys.modules["app.main"])
    else:
        import app.main  # noqa: F401

    from app.main import app
    return app


def assert_status(client: TestClient, method: str, path: str, expected: int, **kwargs) -> None:
    r = client.request(method, path, **kwargs)
    code = r.status_code
    ok = code == expected
    print(f"{method} {path} -> {code}  [{ 'PASS' if ok else f'FAIL expected {expected}' }]")
    if not ok:
        # اطبع جزءًا من الجسم للمساعدة في التشخيص
        text = (r.text or "")[:400]
        print("Response snippet:", text)
        raise AssertionError(f"{method} {path}: {code} != {expected}")


def run_case(title: str, env: Dict[str, str], checks: List[Tuple[str, str, int, dict]]) -> None:
    print("\n=== CASE:", title, "===")
    with patched_environ(env):
        app = load_app_fresh()
        with TestClient(app) as client:
            # صحّة عامة
            assert_status(client, "GET", "/health", 200)
            # اختبارات خاصة بالقضية
            for method, path, expected, kw in checks:
                assert_status(client, method, path, expected, **(kw or {}))


def main():
    # 1) Development (open)
    run_case(
        "Development (env open)",
        {
            "APP_ENV": "development",
            "APP_EXPOSE_ENV_ENDPOINT": "0",
            "APP_ENV_SECRET_TOKEN": "",
        },
        [
            ("GET", "/env", 200, {}),
            ("GET", "/docs", 200, {}),
            ("GET", "/redoc", 200, {}),
        ],
    )

    # 2) Production (closed by default)
    run_case(
        "Production (env closed)",
        {
            "APP_ENV": "production",
            "APP_EXPOSE_ENV_ENDPOINT": "0",
            "APP_ENV_SECRET_TOKEN": "",
        },
        [
            ("GET", "/env", 404, {}),
            ("GET", "/docs", 200, {}),
            ("GET", "/redoc", 200, {}),
        ],
    )

    # 3) Production (open + token-protected)
    run_case(
        "Production (env open + token protected)",
        {
            "APP_ENV": "production",
            "APP_EXPOSE_ENV_ENDPOINT": "1",
            "APP_ENV_SECRET_TOKEN": "supersecret",
        },
        [
            ("GET", "/env", 403, {}),  # بدون التوكن -> 403
            ("GET", "/env", 200, {"headers": {"X-Admin-Token": "supersecret"}}),  # مع التوكن -> 200
        ],
    )

    print("\nAll cases PASS ✅")


if __name__ == "__main__":
    main()
