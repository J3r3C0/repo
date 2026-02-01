import requests
import time
import json

BASE_URL = "http://localhost:8001"

def run_demo():
    print("--- Sheratan Perception Demo ---")
    
    # 1. Check Health
    try:
        resp = requests.get(f"{BASE_URL}/")
        print(f"Core Status: {resp.json().get('status')}")
    except Exception:
        print("Error: Core not running. Start it with START_CORE_ONLY.bat")
        return

    # 2. Ingest Events
    # (id, value, timestamp, channel)
    # Simulating 10 events over 2 channels
    now = int(time.time() * 1000)
    events = []
    for i in range(10):
        events.append((i, 0.5 + (i * 0.05), now + (i * 100), i % 2))
    
    print(f"Ingesting {len(events)} events...")
    requests.post(f"{BASE_URL}/api/event", json={"events": events})

    # 3. Wait for resonance cycle (implicit in engine if processed)
    time.sleep(1)

    # 4. Query Identity (Top-K)
    print("Querying Identity Layer...")
    resp = requests.get(f"{BASE_URL}/api/identity", params={"top_k": 5})
    data = resp.json()
    
    print(f"State Hash: {data.get('state_hash')}")
    print("Selected States:")
    for s in data.get("selected_states", []):
        print(f"  Segment: {s['segment']} | Value: {s['value']:.4f} | Last Seen: {s['last_seen']}")

    # 5. Query Specific Segment
    if data.get("selected_states"):
        seg_id = data["selected_states"][0]["segment"]
        print(f"\nInspecting Segment {seg_id}...")
        seg_resp = requests.get(f"{BASE_URL}/api/identity/{seg_id}")
        print(json.dumps(seg_resp.json(), indent=2))

if __name__ == "__main__":
    run_demo()
