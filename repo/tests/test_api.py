from fastapi.testclient import TestClient
from api_observer import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "running"

def test_event_ingestion():
    # Send a significant event to Trigger resonance
    response = client.post("/events", json=[{"value": 0.8, "channel": 1}])
    assert response.status_code == 200
    assert response.json()["resonance"] > 0
    assert response.json()["cycle"] == 1

def test_state_observation():
    # After one event, state 1 should be visible
    response = client.get("/states?min_val=0.1")
    assert response.status_code == 200
    states = response.json()
    assert any(s["id"] == 1 for s in states)

def test_identity_selection():
    response = client.get("/identity?top_k=1")
    assert response.status_code == 200
    identity = response.json()
    assert len(identity) == 1
    assert identity[0]["state_id"] == 1
