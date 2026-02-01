import requests
import json
import os
import time

BASE_URL = "http://localhost:8001"
RESULT_DIR = r"c:\neuer ordner für allgemein github pulls\sheratan-core\data\webrelay_in"

def trigger_next():
    r = requests.get(f"{BASE_URL}/api/jobs")
    jobs = r.json()
    
    # Find the most recent child job that is still 'working' or 'pending'
    children = [j for j in jobs if j.get('payload', {}).get('_chain_hint', {}).get('role') == 'child']
    if not children:
        print("No child jobs found.")
        return
    
    child = children[-1]
    child_id = child['id']
    print(f"Completing child: {child_id} (Status: {child['status']})")
    
    # Mock result
    res_data = {
        "schema_version": "result_envelope_v1",
        "job_id": child_id,
        "ok": True,
        "result": {
            "summary": "Listed 2 files",
            "data": {
                "files": ["core/main.py", "core/storage.py"]
            }
        }
    }
    
    res_path = os.path.join(RESULT_DIR, f"{child_id}.result.json")
    with open(res_path, 'w') as f:
        json.dump(res_data, f, indent=2)
    
    print(f"Result written to {res_path}")
    print("Waiting for next planning job (llm_step)...")
    
    for _ in range(10):
        time.sleep(2)
        r2 = requests.get(f"{BASE_URL}/api/jobs")
        new_jobs = r2.json()
        llm_steps = [j for j in new_jobs if j.get('payload', {}).get('_chain_hint', {}).get('role') == 'llm_step' and j['id'] != child.get('depends_on', [None])[0]]
        
        # Actually, let's just find the latest job and check if it's an llm_step created after our child
        latest = new_jobs[-1]
        if latest.get('payload', {}).get('_chain_hint', {}).get('role') == 'llm_step' and latest['id'] != child_id:
            print(f"✅ SUCCESS: Next planning job created: {latest['id']}")
            input_data = latest['payload']['params'].get('input', {})
            print("Inspecting tool_results in payload...")
            results = input_data.get('tool_results', [])
            if any(child_id in str(r) for r in results):
                print("   ✅ tool_results propagated correctly!")
            else:
                print("   ❌ tool_results MISSING in next planning phase!")
            return
            
    print("❌ TIMEOUT: Next planning job not created.")

if __name__ == "__main__":
    trigger_next()
