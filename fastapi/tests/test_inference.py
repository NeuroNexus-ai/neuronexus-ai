# Path from repo root: fastapi\tests\test_inference.py
from app.main import app
from starlette.testclient import TestClient

client = TestClient(app)


def test_inference_run():
    payload = {"plugin": "dummy", "task": "infer", "payload": {"text": "hi"}}
    r = client.post("/inference/run", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True


def test_inference_alias():
    payload = {"plugin": "dummy", "task": "infer", "payload": {"text": "hi"}}
    r = client.post("/inference", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True