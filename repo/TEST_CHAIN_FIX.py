import requests
import time
import os
import json

BASE_URL = "http://localhost:8001"
DATA_DIR = r"c:\neuer ordner für allgemein github pulls\sheratan-core\data"
RESULT_DIR = os.path.join(DATA_DIR, "webrelay_in")

def test():
    print("--- MOCK LCP FLOW TEST (v2) ---")
    
    # 1. Create Mission
    mission_data = {"title": "Mock Fix Test v2", "description": "Testing depth derivation"}
    m_resp = requests.post(f"{BASE_URL}/api/missions", json=mission_data).json()
    mission_id = m_resp["id"]
    print(f"Mission: {mission_id}")

    # 2. Create Task
    task_data = {"name": "Mock Task", "kind": "agent_plan", "params": {"chain_id": "mock-chain-" + os.urandom(4).hex()}}
    t_resp = requests.post(f"{BASE_URL}/api/missions/{mission_id}/tasks", json=task_data).json()
    task_id = t_resp["id"]
    print(f"Task: {task_id}")

    # 3. Create Root Job
    job_payload = {
        "payload": {
            "kind": "agent_plan",
            "prompt": "Mock Prompt",
            "_chain_hint": {
                "chain_id": task_data["params"]["chain_id"],
                "root_job_id": "root",
                "role": "llm_step",
                "depth": 0
            }
        },
        "idempotency_key": "mock-trigger-" + os.urandom(4).hex()
    }
    j_resp = requests.post(f"{BASE_URL}/api/tasks/{task_id}/jobs", json=job_payload).json()
    job_id = j_resp["id"]
    print(f"Root Job: {job_id}")

    # 4. Wait for it to be dispatched
    print("Waiting for job to be dispatched...")
    for _ in range(10):
        time.sleep(1)
        j = requests.get(f"{BASE_URL}/api/jobs/{job_id}").json()
        if j["status"] == "working":
            print(f"Job {job_id[:8]} is working.")
            break
    else:
        print("Warning: Job not working yet, but proceeding to write result anyway.")
    
    # 5. Create Mock Result with LCP follow-up
    # compliant with result_envelope_v1 and parse_lcp
    print("Creating mock LCP result...")
    result_data = {
        "schema_version": "result_envelope_v1",
        "ok": True,
        "status": "completed",
        "result": {
            "data": {
                "lcp_version": "1.1.0",
                "jobs": [
                    {
                        "kind": "list_files",
                        "params": {"path": "core"}
                    }
                ]
            }
        },
        "job_id": job_id
    }
    
    result_path = os.path.join(RESULT_DIR, f"{job_id}.result.json")
    with open(result_path, "w") as f:
        json.dump(result_data, f)
    print(f"Result file created at {result_path}")

    # 6. Wait for follow-up job creation
    print("Waiting for follow-up job creation...")
    for _ in range(20):
        time.sleep(2)
        all_jobs = requests.get(f"{BASE_URL}/api/jobs").json()
        followups = [j for j in all_jobs if job_id in j.get("depends_on", [])]
        if followups:
            fj = followups[0]
            print(f"✅ SUCCESS: Follow-up Job created: {fj['id']}")
            hint = fj["payload"].get("_chain_hint", {})
            print(f"   Derived Depth: {hint.get('depth')}")
            print(f"   Kind: {fj['payload'].get('kind')}")
            
            if hint.get('depth') == 1:
                print("🏁 DEPTH DERIVATION VERIFIED!")
            else:
                print(f"❌ DEPTH MISMATCH: Expected 1, got {hint.get('depth')}")
            return
        else:
            print(".", end="", flush=True)
    
    print("\n❌ TIMEOUT: Follow-up job not created.")

if __name__ == "__main__":
    test()
