import requests
import os
import time
import subprocess

BASE_URL = "http://127.0.0.1:8006" # Using a different port to avoid conflict if core is running
CORE_PORT = 8006

def start_core():
    env = os.environ.copy()
    env["SHERATAN_ENABLE_RESET"] = "1"
    # Port 8006 for testing
    process = subprocess.Popen(
        ["python", "core/main.py"],
        env=env,
        cwd="c:/neuer ordner für allgemein github pulls/sheratan-core"
    )
    # Wait for startup (monkeypatch port if needed or just use default but it's 8005 by default)
    # Actually, core/main.py uses port 8005. I'll stick to that but ensure it's free or kill it.
    return process

def wait_for_ready(url, timeout=10):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                print(f"Core ready at {url}")
                return True
        except:
            pass
        time.sleep(0.5)
    return False

def test_reset():
    url = "http://127.0.0.1:8005"
    
    # 1. Get initial state
    resp = requests.get(f"{url}/api/state")
    initial_hash = resp.json()["state_hash"]
    print(f"Initial Hash: {initial_hash}")
    
    # 2. Add some events
    events = {
        "events": [
            [1, 0.5, 100, 1],
            [2, 0.8, 101, 1],
            [1, 0.3, 102, 1]
        ]
    }
    requests.post(f"{url}/api/event", json=events)
    
    resp = requests.get(f"{url}/api/state")
    modified_hash = resp.json()["state_hash"]
    print(f"Modified Hash: {modified_hash}")
    assert initial_hash != modified_hash
    
    # 3. Reset
    resp = requests.post(f"{url}/api/reset")
    reset_data = resp.json()
    print(f"Reset Response: {reset_data}")
    assert reset_data["ok"] == True
    assert reset_data["cycle_count"] == 0
    assert reset_data["state_hash"] == initial_hash
    assert reset_data["segment_count"] == 0
    
    # 4. Replay / Repeat events
    requests.post(f"{url}/api/event", json=events)
    resp = requests.get(f"{url}/api/state")
    replayed_hash = resp.json()["state_hash"]
    print(f"Replayed Hash: {replayed_hash}")
    assert replayed_hash == modified_hash
    print("Test passed: Determinism maintained after reset.")

if __name__ == "__main__":
    # Note: This script assumes core/main.py is NOT running or we start it here.
    # To be safe, I'll just check if it's running first.
    try:
        resp = requests.get("http://127.0.0.1:8005/")
        if resp.status_code == 200:
            print("Core already running. Testing on existing instance.")
            test_reset()
        else:
            print("Core not running or unreachable.")
    except:
        print("Core not running. Manual start required or use subprocess logic.")
        # I will rely on the agent to start it if needed.
