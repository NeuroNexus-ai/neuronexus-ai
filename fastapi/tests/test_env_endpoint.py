import os, importlib, sys
import pytest
from starlette.testclient import TestClient

def reload_app_with_env(env):
  for k, v in env.items(): os.environ[k] = v
  importlib.reload(importlib.import_module("app.core.config"))
  if "app.main" in sys.modules: importlib.reload(sys.modules["app.main"])
  else: importlib.import_module("app.main")
  from app.main import app
  return app

@pytest.mark.parametrize("env,expect", [
  ({"APP_ENV":"development","APP_EXPOSE_ENV_ENDPOINT":"0","APP_ENV_SECRET_TOKEN":""}, [200,200,200,200]),
  ({"APP_ENV":"production","APP_EXPOSE_ENV_ENDPOINT":"0","APP_ENV_SECRET_TOKEN":""}, [200,404,200,200]),
  ({"APP_ENV":"production","APP_EXPOSE_ENV_ENDPOINT":"1","APP_ENV_SECRET_TOKEN":"supersecret"}, [200,403,200,200]),
])
def test_env_endpoint(env, expect):
  app = reload_app_with_env(env)
  with TestClient(app) as c:
    assert c.get("/health").status_code == expect[0]
    r = c.get("/env"); assert r.status_code == expect[1]
    if expect[1] == 403:
      assert c.get("/env", headers={"X-Admin-Token":"supersecret"}).status_code == 200
    assert c.get("/docs").status_code == expect[2]
    assert c.get("/redoc").status_code == expect[3]
