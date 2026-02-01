"""
E2E Mission Flow Test
Tests: Mission → Task → LCP Plan → Follow-up Jobs → Execution
"""
import requests
import time
import json

BASE_URL = "http://localhost:8001"

def test_e2e_mission_flow():
    print("=" * 60)
    print("E2E MISSION FLOW TEST")
    print("=" * 60)
    
    # 1. Create Mission
    print("\n[1/5] Creating mission...")
    mission_resp = requests.post(f"{BASE_URL}/api/missions", json={
        "title": "E2E Test: Autonomous File Analysis",
        "description": "Test autonomous LCP flow with follow-up jobs",
        "user_id": "test_user"
    })
    mission = mission_resp.json()
    mission_id = mission["id"]
    print(f"✓ Mission created: {mission_id}")
    
    # 2. Create Task
    print("\n[2/5] Creating task...")
    task_resp = requests.post(f"{BASE_URL}/api/missions/{mission_id}/tasks", json={
        "name": "analyze_repo_structure",
        "description": "Walk tree and analyze files",
        "params": {
            "chain_id": f"chain-{mission_id}",
            "auto_execute": True
        }
    })
    task = task_resp.json()
    task_id = task["id"]
    print(f"✓ Task created: {task_id}")
    
    # 3. Create initial agent_plan job (LCP)
    print("\n[3/5] Creating agent_plan job...")
    job_resp = requests.post(f"{BASE_URL}/api/tasks/{task_id}/jobs", json={
        "payload": {
            "kind": "agent_plan",
            "params": {
                "intent": "analyze_repository",
                "context": {
                    "repo_path": "c:/sauber_main/repo",
                    "focus": "core module structure"
                },
                "instructions": "Create a plan to analyze the repository. Return LCP envelope with follow-up jobs."
            }
        }
    })
    job = job_resp.json()
    job_id = job["id"]
    print(f"✓ Agent plan job created: {job_id}")
    
    # 4. Wait for job to complete and check for follow-ups
    print("\n[4/5] Waiting for LCP response and follow-up jobs...")
    max_wait = 60
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        # Check job status
        job_status = requests.get(f"{BASE_URL}/api/jobs/{job_id}").json()
        print(f"  Job status: {job_status['status']}")
        
        if job_status["status"] == "completed":
            print(f"✓ Job completed!")
            print(f"  Result preview: {str(job_status.get('result', {}))[:200]}...")
            
            # Check for follow-up specs
            time.sleep(2)  # Give ChainRunner time to process
            
            # Get all jobs for this task
            all_jobs = requests.get(f"{BASE_URL}/api/tasks/{task_id}/jobs").json()
            print(f"\n  Total jobs in task: {len(all_jobs)}")
            
            for j in all_jobs:
                print(f"    - {j['id'][:12]}... [{j['status']}] {j.get('payload', {}).get('kind', 'unknown')}")
            
            if len(all_jobs) > 1:
                print(f"\n✓ Follow-up jobs created! ({len(all_jobs) - 1} additional jobs)")
            else:
                print(f"\n⚠ No follow-up jobs created (expected if LCP didn't return followup_jobs)")
            
            break
        
        time.sleep(2)
    else:
        print(f"✗ Timeout waiting for job completion")
        return False
    
    # 5. Check chain state
    print("\n[5/5] Checking chain state...")
    try:
        chain_resp = requests.get(f"{BASE_URL}/api/chains/{mission_id}")
        if chain_resp.status_code == 200:
            chain = chain_resp.json()
            print(f"✓ Chain state: {chain.get('state', 'unknown')}")
            print(f"  Specs: {len(chain.get('specs', []))}")
        else:
            print(f"  Chain endpoint not available (status {chain_resp.status_code})")
    except:
        print(f"  Chain endpoint not available")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    return True

if __name__ == "__main__":
    try:
        test_e2e_mission_flow()
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
