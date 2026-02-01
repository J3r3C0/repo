#!/usr/bin/env python3
"""
Test script to verify job creation, follow-up handling, and context injection.
This script uses the correct API schema (TaskCreate.name instead of title).
"""
import requests
import time
import json
import os
from pathlib import Path

BASE_URL = "http://localhost:8001"

def run_test():
    print("=== STARTING AUTONOMOUS FLOW TEST (v2) ===")
    
    # Prefix for idempotency and unique IDs
    ts = int(time.time())
    
    # 1. CREATE MISSION
    print("\n[1] Creating Mission...")
    mission_data = {
        "title": f"Injection Test {ts}",
        "description": "Verifying artifact injection and follow-up loops",
        "user_id": "alice"
    }
    resp = requests.post(f"{BASE_URL}/api/missions", json=mission_data)
    if resp.status_code != 200:
        print(f"❌ Mission creation failed: {resp.text}")
        return
    mission = resp.json()
    mission_id = mission["id"]
    print(f"✅ Mission {mission_id[:8]} created.")

    # 2. CREATE TASK (Correct schema: 'name', not 'title')
    print("\n[2] Creating Task...")
    chain_id = f"chain-{ts}"
    task_data = {
        "name": f"Planning Task {ts}",
        "description": "Generates follow-up work",
        "kind": "agent_plan",
        "params": {"chain_id": chain_id}
    }
    resp = requests.post(f"{BASE_URL}/api/missions/{mission_id}/tasks", json=task_data)
    if resp.status_code != 200:
        print(f"❌ Task creation failed: {resp.text}")
        return
    task = resp.json()
    task_id = task["id"]
    print(f"✅ Task {task_id[:8]} created with chain_id={chain_id}")

    # 3. ANALYZE CURRENT CONTEXT (Artifact Injection)
    # We want to see if recent results are injected.
    # We'll simulate this by manually creating a completed job with an artifact first,
    # or just relying on the fact that if this is a chain, the dispatcher should find it.
    
    # 4. CREATE JOB
    print("\n[3] Creating Trigger Job...")
    # We'll use a specific prompt that usually triggers LCP responses if the model is smart.
    # We also include 'context' in the payload to see if it survives.
    job_payload = {
        "payload": {
            "kind": "agent_plan",
            "prompt": "List the contents of the 'core' directory. Respond with a JSON LCP envelope containing exactly one follow-up job with kind 'list_files' and params 'path: core'.",
            "context": {
                "hint": "SHERATAN_SECRET_MARKER",
                "target": "core/"
            }

        },
        "priority": "normal",
        "idempotency_key": f"e2e-job-{ts}"
    }
    resp = requests.post(f"{BASE_URL}/api/tasks/{task_id}/jobs", json=job_payload)
    if resp.status_code != 200:
        print(f"❌ Job creation failed: {resp.text}")
        return
    job = resp.json()
    job_id = job["id"]
    print(f"✅ Job {job_id[:8]} created (status: {job['status']}).")

    # 5. MONITOR & VERIFY
    print("\n[4] Monitoring for execution and follow-ups...")
    print("Looking for .job.json in data/webrelay_out/ to verify injection...")
    
    # Wait for the dispatcher to create the file
    found_file = None
    for i in range(10):
        time.sleep(2)
        job_file = Path(f"data/webrelay_out/{job_id}.job.json")
        if job_file.exists():
            found_file = job_file
            print(f"✅ Job file found: {job_file}")
            break
        print(f"   [{i*2}s] Waiting for dispatcher...")

    if found_file:
        with open(found_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Check for context in payload
            if data.get("payload", {}).get("params", {}).get("context"):
                print("✅ SUCCESS: Context injected into job file!")
            else:
                # Check legacy or unified locations
                print(f"ℹ️ Job file keys: {list(data.get('payload', {}).keys())}")
                if "params" in data.get("payload", {}):
                     print(f"   Params: {list(data['payload']['params'].keys())}")

    print("\n[5] Waiting for LLM result and follow-up jobs...")
    max_wait = 60
    start_wait = time.time()
    while time.time() - start_wait < max_wait:
        # Check for new jobs in the task
        resp = requests.get(f"{BASE_URL}/api/jobs")
        all_jobs = resp.json()
        
        # Original job status
        our_job = next((j for j in all_jobs if j["id"] == job_id), None)
        # Follow-up jobs (jobs that depend on original)
        followups = [j for j in all_jobs if job_id in j.get("depends_on", [])]
        
        print(f"   [{int(time.time()-start_wait)}s] Job Status: {our_job['status'] if our_job else '?'}, Follow-ups: {len(followups)}", end="\r")
        
        if len(followups) > 0:
            print(f"\n✅ SUCCESS: {len(followups)} follow-up job(s) created autonomously!")
            for fj in followups:
                print(f"   - {fj['id'][:8]}: {fj['payload'].get('kind')} ({fj['status']})")
            return
            
        time.sleep(5)

    print("\n⏱️ Timeout: No follow-up jobs detected. LLM might not have returned an LCP response.")

if __name__ == "__main__":
    run_test()
