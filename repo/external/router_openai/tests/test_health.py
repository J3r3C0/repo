from fastapi.testclient import TestClient
from sheratan_router_openai.adapter import app

def test_health():
    c = TestClient(app)
    r = c.get("/health")
    assert r.status_code == 200
    assert r.json().get("ok") is True
