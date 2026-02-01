import pytest
import requests
import time
import subprocess
import os

BASE_URL = "http://localhost:8001"

@pytest.fixture(scope="module", autouse=True)
def observer_api():
    # Start the observer API in the background
    env = os.environ.copy()
    env["DETERMINISTIC_MODE"] = "1"
    proc = subprocess.Popen(["python", "api_observer.py"], env=env)
    time.sleep(3) # Wait for startup
    yield
    proc.terminate()

def test_phase1_status_ok():
    r = requests.get(f"{BASE_URL}/api/system/phase1")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "OK"
    assert data["policy_id"] == "sheratan-phase1-core"
    assert data["deterministic_mode"] == True

def test_actionable_perception_api():
    # Post some events
    payload = [{"value": 1.0, "channel": 1}]
    r = requests.post(f"{BASE_URL}/events", json=payload)
    assert r.status_code == 200
    
    # Check states for score and recommendation
    r = requests.get(f"{BASE_URL}/states")
    assert r.status_code == 200
    states = r.json()
    assert len(states) > 0
    state = states[0]
    assert "score" in state
    assert "recommendation" in state
    assert state["recommendation"] is not None
