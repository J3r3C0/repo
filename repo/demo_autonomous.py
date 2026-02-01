#!/usr/bin/env python3
import requests
import time
import json
import uuid
import os
from pathlib import Path

BASE_URL = "http://localhost:8001"

def run_autonomous_demo():
    print("=== STARTING AUTONOMOUS CONTEXT DEMO ===")
    
    ts = int(time.time())
    
    print(f"\n[1] Creating Mission...")
    m_resp = requests.post(f"{BASE_URL}/api/missions", json={
        "title": f"Autonomous Demo {ts}",
        "description": "Testing context injection"
    })
    if m_resp.status_code != 200:
        print(f"Failed to create mission: {m_resp.text}")
        return
    mission_id = m_resp.json()["id"]

    # Create the task
    print(f"[2] Creating Task...")
    t_resp = requests.post(f"{BASE_URL}/api/missions/{mission_id}/tasks", json={
        "name": f"Context Task {ts}",
        "kind": "agent_plan",
        "params": {"chain_id": f"chain-{ts}"}
    })
    if t_resp.status_code != 200:
        print(f"Failed to create task: {t_resp.text}")
        return
    task_id = t_resp.json()["id"]

    # 3. TRIGGER PLANNING JOB
    print(f"\n[3] Triggering planning job...")
    job_payload = {
        "payload": {
            "kind": "agent_plan",
            "prompt": "List the files you found in the context and confirm the marker 'CORE_V2_ACTIVE'.",
            "context": {
                "AUTONOMOUS_MARKER": "CORE_V2_ACTIVE",
                "detected_files": ["main.py", "storage.py", "models.py", "config.py", "webrelay_bridge.py"]
            }
        },
        "idempotency_key": f"demo-job-{ts}"
    }

    resp = requests.post(f"{BASE_URL}/api/tasks/{task_id}/jobs", json=job_payload)
    if resp.status_code != 200:
        print(f"Failed to create job: {resp.text}")
        return
    job_id = resp.json()["id"]
    
    print(f"✅ Job {job_id[:8]} created.")
    print("\nWATCH GPT NOW.")

if __name__ == "__main__":
    run_autonomous_demo()
