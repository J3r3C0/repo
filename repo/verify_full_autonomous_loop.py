#!/usr/bin/env python3
import requests
import time
import json
import os

BASE_URL = "http://localhost:8001"

def run_test():
    print("=== STARTING FULL AUTONOMOUS LOOP TEST ===")
    
    # 1. Create Mission
    print("\n[1] Creating Mission...")
    mission_data = {
        "title": "E2E Autonomous Test",
        "description": "Test follow-up job creation with context injection",
        "user_id": "alice",
        "status": "active"
    }
    resp = requests.post(f"{BASE_URL}/api/missions", json=mission_data)
    if resp.status_code != 200:
        print(f"FAILED: {resp.text}")
        return
    mission = resp.json()
    mission_id = mission["id"]
    print(f"SUCCESS: Mission {mission_id[:8]} created.")

    # 2. Create Task
    print("\n[2] Creating Task...")
    task_data = {
        "name": "Autonomous Planning Task",
        "description": "Task that generates more work",
        "kind": "agent_plan",
        "params": {"chain_id": "chain-" + os.urandom(4).hex()}
    }
    resp = requests.post(f"{BASE_URL}/api/missions/{mission_id}/tasks", json=task_data)
    if resp.status_code != 200:
        print(f"FAILED: {resp.text}")
        return
    task = resp.json()
    task_id = task["id"]
    print(f"SUCCESS: Task {task_id[:8]} created.")

    # 3. Create Job (The Trigger)
    print("\n[3] Creating Trigger Job...")
    # This prompt is designed to make the LLM return an LCP result with follow-up jobs
    job_payload = {
        "payload": {
            "kind": "agent_plan",
            "prompt": "Inspect the system security and create exactly one follow-up job to check the logs directory.",
            "context": {
                "injected_system_context": "The system is currently running in a test environment. Ports are 8001 (Core) and 3000 (WebRelay).",
                "target_directory": "logs/",
                "security_info": "Encryption is enabled for all job files."
            }
        },
        "priority": "normal",
        "idempotency_key": "e2e-trigger-" + os.urandom(4).hex()
    }
    resp = requests.post(f"{BASE_URL}/api/tasks/{task_id}/jobs", json=job_payload)
    if resp.status_code != 200:
        print(f"FAILED: {resp.text}")
        return
    job = resp.json()
    job_id = job["id"]
    print(f"SUCCESS: Job {job_id[:8]} created.")

    # 4. Wait for processing
    print("\n[4] Waiting for Job Execution and Follow-up Creation...")
    print("This involves WebRelay (LLM call) and Dispatcher sync.")
    
    max_wait = 120 # 2 minutes
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        # Check original job status
        job_resp = requests.get(f"{BASE_URL}/api/tasks/{task_id}")
        # We check all jobs to see if new ones appeared in this task
        all_jobs_resp = requests.get(f"{BASE_URL}/api/jobs")
        all_jobs = all_jobs_resp.json()
        
        our_job = next((j for j in all_jobs if j["id"] == job_id), None)
        followups = [j for j in all_jobs if job_id in j.get("depends_on", [])]
        
        status = our_job["status"] if our_job else "unknown"
        print(f"Current Status: {status} | Follow-up Jobs: {len(followups)}", end="\r")
        
        if len(followups) > 0:
            print(f"\n✅ SUCCESS: Found {len(followups)} follow-up job(s)!")
            for fj in followups:
                print(f"   - Follow-up Job {fj['id'][:8]}: kind={fj['payload'].get('kind')}")
            break
            
        if status == "failed":
            print(f"\n❌ FAILED: Trigger job failed. Result: {our_job.get('result')}")
            break
            
        time.sleep(5)
    else:
        print(f"\n⏱️ TIMEOUT: No follow-up jobs created within {max_wait}s.")

    print("\nTest completed.")

if __name__ == "__main__":
    run_test()
