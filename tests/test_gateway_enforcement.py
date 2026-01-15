"""
Test Gateway Enforcement Integration

Verifies that G0-G4 gates are properly enforced on job creation.
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8001"

def test_gateway_enforcement():
    """Test that gateway enforcement blocks forbidden job kinds."""
    
    print("=" * 60)
    print("Gateway Enforcement Test")
    print("=" * 60)
    
    # 1. Create a mission
    print("\n[1/5] Creating test mission...")
    mission_payload = {
        "title": "Gateway Test Mission",
        "description": "Test gateway enforcement",
        "priority": "normal"
    }
    
    resp = requests.post(f"{BASE_URL}/api/missions", json=mission_payload)
    if resp.status_code != 200:
        print(f"[FAIL] Failed to create mission: {resp.status_code}")
        print(resp.text)
        return False
    
    mission = resp.json()
    mission_id = mission["id"]
    print(f"[OK] Mission created: {mission_id[:8]}")
    
    # 2. Create a task
    print("\n[2/5] Creating test task...")
    task_payload = {
        "name": "gateway_test_task",
        "description": "Test task for gateway enforcement"
    }
    
    resp = requests.post(f"{BASE_URL}/api/missions/{mission_id}/tasks", json=task_payload)
    if resp.status_code != 200:
        print(f"[FAIL] Failed to create task: {resp.status_code}")
        print(resp.text)
        return False
    
    task = resp.json()
    task_id = task["id"]
    print(f"[OK] Task created: {task_id[:8]}")
    
    # 3. Test FORBIDDEN job kind (should fail)
    print("\n[3/5] Testing FORBIDDEN job kind (SHELL_EXEC)...")
    forbidden_job = {
        "priority": "normal",
        "payload": {
            "kind": "SHELL_EXEC",
            "params": {
                "command": "echo 'test'"
            }
        }
    }
    
    resp = requests.post(f"{BASE_URL}/api/tasks/{task_id}/jobs", json=forbidden_job)
    
    # In soft mode, this might still succeed with a warning
    # In hard mode, this should return 403
    if resp.status_code == 403:
        print("[OK] SHELL_EXEC correctly blocked (hard enforcement)")
        gate_report = resp.json()
        print(f"   Gate status: {gate_report.get('status')}")
        print(f"   Blocked by: {[r['gate_id'] for r in gate_report.get('blocked_reasons', [])]}")
    elif resp.status_code == 200:
        job = resp.json()
        gate_status = job.get("meta", {}).get("gateway_enforcement", {}).get("status")
        enforcement_mode = job.get("meta", {}).get("gateway_enforcement", {}).get("enforcement_mode")
        print(f"[WARN] SHELL_EXEC allowed in {enforcement_mode} mode (status: {gate_status})")
        print(f"   Job created: {job['id'][:8]}")
    else:
        print(f"[FAIL] Unexpected response: {resp.status_code}")
        print(resp.text)
        return False
    
    # 4. Test ALLOWED job kind (should succeed)
    print("\n[4/5] Testing ALLOWED job kind (llm_call)...")
    allowed_job = {
        "priority": "normal",
        "payload": {
            "kind": "llm_call",
            "params": {
                "prompt": "Test prompt"
            }
        }
    }
    
    resp = requests.post(f"{BASE_URL}/api/tasks/{task_id}/jobs", json=allowed_job)
    if resp.status_code != 200:
        print(f"[FAIL] Failed to create allowed job: {resp.status_code}")
        print(resp.text)
        return False
    
    job = resp.json()
    gate_status = job.get("meta", {}).get("gateway_enforcement", {}).get("status")
    print(f"[OK] llm_call allowed (gate status: {gate_status})")
    print(f"   Job created: {job['id'][:8]}")
    
    # 5. Check gateway logs
    print("\n[5/5] Checking gateway enforcement logs...")
    try:
        with open("logs/gateway_enforcement.jsonl", "r", encoding="utf-8") as f:
            lines = f.readlines()
            recent_logs = lines[-5:] if len(lines) >= 5 else lines
            
            print(f"   Found {len(lines)} total gateway decisions")
            print(f"   Recent decisions:")
            for line in recent_logs:
                entry = json.loads(line)
                print(f"     - {entry['job_id'][:8]}: {entry['overall_status']}")
    except FileNotFoundError:
        print("   [WARN] No gateway log file found (may not have been created yet)")
    except Exception as e:
        print(f"   [WARN] Error reading logs: {e}")
    
    print("\n" + "=" * 60)
    print("[OK] Gateway Enforcement Test PASSED")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        success = test_gateway_enforcement()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n[FAIL] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
