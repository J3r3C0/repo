import requests
import time
import json
import uuid

CORE_URL = "http://127.0.0.1:8001"

def create_mission():
    print("--- Phase 1: Environment Setup & Creation ---")
    
    # 1. Check Connectivity
    try:
        resp = requests.get(f"{CORE_URL}/api/jobs", timeout=5)
        if resp.status_code == 200:
            print("Connected to Core API.")
    except Exception as e:
        print(f"ERROR: Cannot connect to Core at {CORE_URL}: {e}")
        return None, None

    # 2. Create Mission
    mission_payload = {
        "title": "2-Round Context Proof",
        "description": "Proof of context preservation between discovery and analysis turns.",
        "user_id": "alice"
    }
    print("Creating mission...")
    resp = requests.post(f"{CORE_URL}/api/missions", json=mission_payload)
    if resp.status_code != 200:
        print(f"Mission creation FAILED: {resp.status_code} - {resp.text}")
        return None, None
    mission = resp.json()
    mission_id = mission["id"]
    print(f"Mission Created: {mission_id}")

    # 3. Create Task
    prompt = (
        "AUTONOMOUS MISSION: Find the file 'core/main.py' and tell me the value of "
        "the constant 'HASH_WRITES_COUNTER'.\n"
        "STEPS REQUIRED:\n"
        "1. Discover the project tree using 'walk_tree' to locate 'core/main.py'.\n"
        "2. READ the content of 'core/main.py'.\n"
        "3. Provide the value of 'HASH_WRITES_COUNTER'."
    )
    task_payload = {
        "name": "2-Round Context Proof Task",
        "params": {
            "chain_id": mission_id,
            "user_request": prompt
        }
    }
    print(f"Creating task for mission {mission_id}...")
    resp = requests.post(f"{CORE_URL}/api/missions/{mission_id}/tasks", json=task_payload)
    if resp.status_code != 200:
        print(f"Task creation FAILED: {resp.status_code} - {resp.text}")
        return None, None
    task = resp.json()
    task_id = task["id"]
    print(f"Task Created: {task_id}")

    # 4. Create Root Job (agent_plan)
    # MUST satisfy models.JobCreate schema (payload, priority, etc)
    job_payload = {
        "payload": {
            "kind": "agent_plan",
            "params": {
                "user_request": prompt,
                "project_root": "."
            },
            "_chain_hint": {
                "chain_id": mission_id,
                "role": "llm_step",
                "depth": 0
            }
        },
        "priority": "normal",
        "depends_on": [] # Explicitly empty for root
    }
    print(f"Launching autonomous chain for task {task_id}...")
    resp = requests.post(f"{CORE_URL}/api/tasks/{task_id}/jobs", json=job_payload)
    if resp.status_code != 200:
        print(f"Root job creation FAILED: {resp.status_code} - {resp.text}")
        return None, None
    print(f"Root Job Created: {resp.json()['id']}")
    
    return mission_id, task_id

def monitor_loop(mission_id, task_id):
    print(f"--- Phase 2: Monitoring (Max 15 minutes) ---")
    seen_jobs = set()
    start_time = time.time()
    
    while time.time() - start_time < 900:
        try:
            resp = requests.get(f"{CORE_URL}/api/jobs")
            jobs = [j for j in resp.json() if j["task_id"] == task_id]
            
            for j in jobs:
                jid = j["id"]
                if jid not in seen_jobs:
                    seen_jobs.add(jid)
                    kind = j["payload"].get("kind", "unknown")
                    print(f"[*] NEW JOB: {jid[:8]} ({kind}) - Status: {j['status']}")
                
                if kind == "agent_plan" and j["status"] == "completed":
                    hint = j["payload"].get("_chain_hint", {})
                    # Round 2 planning happens at depth 2 (0=plan1, 1=walk, 2=plan2/interpret)
                    if hint.get("depth", 0) >= 2:
                        res = j.get("result")
                        if res and (res.get("type") == "final_answer" or "answer" in res):
                            print("\n" + "="*50)
                            print("🎉 E2E PROOF SUCCESSFUL!")
                            print("Evolution of context confirmed through multiple turns.")
                            print("FINAL ANSWER:", json.dumps(res, indent=2))
                            print("="*50 + "\n")
                            return True
        except Exception as e:
            print(f"Monitor error: {e}")
        time.sleep(15)
    
    print("❌ Proof timed out.")
    return False

if __name__ == "__main__":
    m_id, t_id = create_mission()
    if m_id:
        monitor_loop(m_id, t_id)
