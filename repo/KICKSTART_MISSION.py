#!/usr/bin/env python3
import requests
import uuid
import time

# Configuration
CORE_API_URL = "http://localhost:8001"

def kickstart():
    print("=== SHERATAN KICKSTART MISSION ===")
    
    # 1. Create a Mission
    print("\n[1/3] Creating Mission...")
    mission_data = {
        "title": "Autonomous Evolution Mission",
        "description": "A live test of the Mind-Body loop. GPT plans, Nodes execute, context grows."
    }
    
    resp = requests.post(f"{CORE_API_URL}/api/missions", json=mission_data)
    if resp.status_code != 200:
        print(f"FAILED (Mission): {resp.text}")
        return
    
    # CRITICAL: Use the ID returned by the server, not a client-side one!
    mission = resp.json()
    mission_id = mission["id"]
    print(f"✅ Mission created with ID: {mission_id}")

    # 2. Add an initial Task
    print(f"[2/3] Adding Task to Mission {mission_id[:8]}...")
    task_data = {
        "name": "Analyze Core Structure",
        "description": "List the files in the 'core' directory to build the world model.",
        "kind": "agent_plan"
    }
    
    resp = requests.post(f"{CORE_API_URL}/api/missions/{mission_id}/tasks", json=task_data)
    if resp.status_code != 200:
        print(f"FAILED (Task): {resp.text}")
        return
    task_id = resp.json()["id"]
    print(f"✅ Task created with ID: {task_id}")

    # 3. Create the first Job
    print("[3/3] Launching First Job (LCP Spec)...")
    job_payload = {
        "payload": {
            "kind": "agent_plan",
            "prompt": "List the contents of the 'core' directory. Respond with a JSON LCP envelope containing exactly one follow-up job with kind 'list_files' and params 'path: core'.",
            "_chain_hint": {
                "chain_id": task_id,
                "root_job_id": "root",
                "role": "llm_step",
                "depth": 0
            }
        },
        "idempotency_key": f"kickstart-{mission_id}"
    }
    
    resp = requests.post(f"{CORE_API_URL}/api/tasks/{task_id}/jobs", json=job_payload)
    if resp.status_code != 200:
        print(f"FAILED (Job): {resp.text}")
        return
    
    job_id = resp.json()["id"]
    print(f"\n🚀 ALL SYSTEMS GO! Mission is LIVE.")
    print(f"Job ID: {job_id}")
    print("\n--- NEXT STEPS ---")
    print("1. SWITCH TO GPT WINDOW: You will see WebRelay sending the prompt.")
    print("2. WAIT FOR NODES: Once GPT responds, Host-A/B will execute the command.")
    print("3. CHECK UI: Refresh your DecisionView to see the new trace entry.")

if __name__ == "__main__":
    kickstart()
