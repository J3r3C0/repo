#!/usr/bin/env python3
"""
End-to-End Test: Mission → Task → Job → Follow-up Jobs + Context Injection
Tests the complete autonomous loop with LCP action handling.
"""
import sys
import os
import time
import json
import requests
from pathlib import Path

# Add core to path
sys.path.insert(0, os.getcwd())

BASE_URL = "http://localhost:8001"

def create_mission():
    """Create a test mission."""
    print("\n[1/5] Creating Mission...")
    resp = requests.post(f"{BASE_URL}/api/missions", json={
        "title": "E2E Test: Autonomous Job Chain",
        "description": "Test mission to verify follow-up job creation and context injection",
        "priority": "high"
    })
    resp.raise_for_status()
    mission = resp.json()
    print(f"✅ Mission created: {mission['id'][:8]}")
    return mission

def create_task(mission_id):
    """Create a task for the mission."""
    print("\n[2/5] Creating Task...")
    resp = requests.post(f"{BASE_URL}/api/missions/{mission_id}/tasks", json={
        "title": "Analyze system and create follow-up work",
        "description": "Use agent_plan to analyze the system and create follow-up jobs"
    })
    resp.raise_for_status()
    task = resp.json()
    print(f"✅ Task created: {task['id'][:8]}")
    return task

def create_job(task_id):
    """Create an agent_plan job that will trigger follow-ups."""
    print("\n[3/5] Creating Job (agent_plan with context injection)...")
    
    # Context injection: provide system info
    context = {
        "system_info": {
            "repo_path": "c:/neuer ordner für allgemein github pulls/sheratan-core",
            "core_modules": ["core/main.py", "core/dispatcher.py", "core/chain_runner.py"],
            "recent_changes": "Port configuration updated to 8001"
        },
        "instructions": "Analyze the core modules and create 2 follow-up jobs: one to list files in core/, another to check the config"
    }
    
    resp = requests.post(f"{BASE_URL}/api/tasks/{task_id}/jobs", json={
        "kind": "agent_plan",
        "payload": {
            "kind": "agent_plan",
            "prompt": "Analyze the Sheratan Core system and create follow-up jobs to inspect the codebase",
            "context": context  # Context injection
        },
        "priority": "high",
        "idempotency_key": f"e2e-test-{int(time.time())}"
    })
    resp.raise_for_status()
    job = resp.json()
    print(f"✅ Job created: {job['id'][:8]}")
    print(f"   Context injected: {len(json.dumps(context))} bytes")
    return job

def wait_for_completion(job_id, timeout=60):
    """Wait for job to complete."""
    print(f"\n[4/5] Waiting for job {job_id[:8]} to complete...")
    start = time.time()
    
    while time.time() - start < timeout:
        resp = requests.get(f"{BASE_URL}/api/jobs/{job_id}")
        resp.raise_for_status()
        job = resp.json()
        
        status = job.get("status")
        print(f"   Status: {status}", end="\r")
        
        if status == "completed":
            print(f"\n✅ Job completed in {int(time.time() - start)}s")
            return job
        elif status == "failed":
            print(f"\n❌ Job failed: {job.get('result', {}).get('error', 'Unknown error')}")
            return job
        
        time.sleep(2)
    
    print(f"\n⏱️ Timeout after {timeout}s")
    return None

def check_followup_jobs(original_job_id):
    """Check if follow-up jobs were created."""
    print(f"\n[5/5] Checking for follow-up jobs...")
    
    # Get all jobs
    resp = requests.get(f"{BASE_URL}/api/jobs")
    resp.raise_for_status()
    all_jobs = resp.json()
    
    # Find jobs that depend on our original job
    followups = [j for j in all_jobs if original_job_id in j.get("depends_on", [])]
    
    if followups:
        print(f"✅ Found {len(followups)} follow-up job(s):")
        for fj in followups:
            print(f"   - {fj['id'][:8]}: {fj['payload'].get('kind', 'unknown')} (status: {fj['status']})")
        return followups
    else:
        print("❌ No follow-up jobs found")
        return []

def main():
    print("=" * 60)
    print("E2E Test: Complete Autonomous Job Flow")
    print("=" * 60)
    
    try:
        # 1. Create mission
        mission = create_mission()
        
        # 2. Create task
        task = create_task(mission["id"])
        
        # 3. Create job with context injection
        job = create_job(task["id"])
        
        # 4. Wait for completion
        completed_job = wait_for_completion(job["id"])
        
        if not completed_job:
            print("\n❌ TEST FAILED: Job did not complete")
            return 1
        
        # 5. Check for follow-up jobs
        followups = check_followup_jobs(job["id"])
        
        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Mission ID: {mission['id'][:8]}")
        print(f"Task ID: {task['id'][:8]}")
        print(f"Job ID: {job['id'][:8]}")
        print(f"Job Status: {completed_job.get('status')}")
        print(f"Follow-up Jobs: {len(followups)}")
        
        if completed_job.get("status") == "completed" and len(followups) > 0:
            print("\n✅ TEST PASSED: Complete autonomous flow working!")
            return 0
        else:
            print("\n⚠️ TEST INCOMPLETE: Check logs for details")
            return 1
            
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
