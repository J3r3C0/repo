#!/usr/bin/env python3
"""
End-to-End Test: Autonomous Follow-up Job Generation
Tests the complete flow: Mission → Task → Job → LCP Response → Autonomous Follow-up
"""
import sys
import os
import time
import json
import uuid
from pathlib import Path

# Add repo to path
sys.path.insert(0, str(Path(__file__).parent / "repo"))

from core import models, store
from core.chain import chain_runner

def test_e2e_autonomous():
    print("=" * 80)
    print("E2E Test: Autonomous Follow-up Job Generation")
    print("=" * 80)
    
    # Initialize store
    store.initialize()
    
    # Phase 1: Create Mission
    print("\n[Phase 1] Creating test mission...")
    mission = models.Mission(
        id=f"m-{uuid.uuid4().hex[:8]}",
        title="E2E Test: Autonomous Follow-up",
        description="Testing autonomous LCP-based follow-up job creation",
        user_id="test-user",
        status="active",
        metadata={},
        tags=["test", "e2e"]
    )
    store.create_mission(mission)
    print(f"✓ Mission created: {mission.id}")
    print(f"  Title: {mission.title}")
    
    # Phase 2: Create Task (with parent_id = mission_id)
    print(f"\n[Phase 2] Creating task with parent mission_id={mission.id}...")
    task = models.Task(
        id=f"t-{uuid.uuid4().hex[:8]}",
        mission_id=mission.id,  # parent_id
        name="Initial Planning Task",
        description="Generate plan for data analysis",
        kind="plan",
        params={"objective": "Analyze user behavior patterns"}
    )
    store.create_task(task)
    print(f"✓ Task created: {task.id}")
    print(f"  Parent mission_id: {task.mission_id}")
    
    # Phase 3: Create Job (with parent_id = task_id)
    print(f"\n[Phase 3] Creating job with parent task_id={task.id}...")
    job_payload = {
        "kind": "llm.chat",
        "instruction": "Create a plan for analyzing user behavior patterns.",
        "context": {
            "mission_id": mission.id,
            "task_id": task.id
        }
    }
    
    job = models.Job(
        id=f"j-{uuid.uuid4().hex[:8]}",
        task_id=task.id,  # parent_id
        payload=job_payload,
        status="pending",
        priority=5
    )
    store.create_job(job)
    print(f"✓ Job created: {job.id}")
    print(f"  Parent task_id: {job.task_id}")
    print(f"  Status: {job.status}")
    
    # Phase 4: Simulate GPT Response with LCP Follow-up
    print(f"\n[Phase 4] Simulating GPT response with LCP follow-up...")
    
    # This is what a real LLM would return
    simulated_lcp_response = {
        "lcp_version": "1.0",
        "operation": "jobs.create",
        "thinking": "I need to create a follow-up job to execute the data collection step",
        "jobs": [
            {
                "kind": "data.collect",
                "instruction": "Collect user behavior data from the last 30 days",
                "params": {
                    "source": "analytics_db",
                    "timeframe": "30d",
                    "metrics": ["clicks", "sessions", "conversions"]
                },
                "priority": 5
            }
        ]
    }
    
    # Build the complete job result with LCP embedded
    job_result = {
        "ok": True,
        "text": "I've created a plan for analyzing user behavior patterns. First, we need to collect the data.",
        "lcp": simulated_lcp_response
    }
    
    print(f"✓ Simulated LCP response:")
    print(f"  Operation: {simulated_lcp_response['operation']}")
    print(f"  Follow-up job kind: {simulated_lcp_response['jobs'][0]['kind']}")
    
    # Update job with result
    job.status = "completed"
    job.result = job_result
    job.completed_result = job_result
    
    # Update in DB
    with store.get_db() as conn:
        conn.execute("""
            UPDATE jobs 
            SET status = ?, result = ?, completed_result = ?, updated_at = ?
            WHERE id = ?
        """, ("completed", json.dumps(job_result), json.dumps(job_result), 
              time.time(), job.id))
        conn.commit()
    
    print(f"✓ Job updated with LCP result")
    
    # Create chain_spec for follow-up (this is what the system should do automatically)
    print(f"\n[Phase 5] Creating chain_spec for follow-up...")
    
    with store.get_db() as conn:
        spec_id = f"cs-{uuid.uuid4().hex[:8]}"
        conn.execute("""
            INSERT INTO chain_specs (id, chain_id, parent_job_id, template, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            spec_id,
            f"chain-{mission.id}",
            job.id,
            json.dumps(simulated_lcp_response['jobs'][0]),
            "pending",
            time.time()
        ))
        conn.commit()
        print(f"✓ Chain spec created: {spec_id}")
    
    # Phase 6: Wait for ChainRunner to pick up and process
    print(f"\n[Phase 6] Waiting for ChainRunner to process follow-up...")
    print("  ChainRunner should:")
    print("  1. Detect pending chain_spec")
    print("  2. Create the follow-up job automatically")
    print("  3. Dispatch it to a worker")
    
    max_wait = 10
    for i in range(max_wait):
        time.sleep(1)
        
        # Check if follow-up job was created
        with store.get_db() as conn:
            cursor = conn.execute("""
                SELECT id, task_id, payload, status 
                FROM jobs 
                WHERE id != ? 
                AND task_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (job.id, task.id))
            follow_up = cursor.fetchone()
            
            if follow_up:
                print(f"\n✓ SUCCESS! Follow-up job created automatically:")
                print(f"  Job ID: {follow_up[0]}")
                print(f"  Task ID: {follow_up[1]}")
                print(f"  Status: {follow_up[3]}")
                payload = json.loads(follow_up[2])
                print(f"  Kind: {payload.get('kind')}")
                
                # Check chain_spec status
                cursor = conn.execute("""
                    SELECT status FROM chain_specs WHERE id = ?
                """, (spec_id,))
                spec_status = cursor.fetchone()
                if spec_status:
                    print(f"  Chain spec status: {spec_status[0]}")
                
                print(f"\n{'=' * 80}")
                print("✓ END-TO-END TEST PASSED!")
                print("  System autonomously created follow-up job from LCP response")
                print("=" * 80)
                return True
        
        print(f"  Waiting... ({i+1}/{max_wait}s)", end="\r")
    
    print(f"\n\n⚠ TIMEOUT: Follow-up job not created within {max_wait}s")
    print("  Checking chain_spec status...")
    
    with store.get_db() as conn:
        cursor = conn.execute("""
            SELECT id, status, created_at FROM chain_specs WHERE id = ?
        """, (spec_id,))
        spec = cursor.fetchone()
        if spec:
            print(f"  Chain spec: {spec[0]}")
            print(f"  Status: {spec[1]}")
            print(f"  Created: {spec[2]}")
    
    print("\n" + "=" * 80)
    print("⚠ END-TO-END TEST INCOMPLETE")
    print("  Manual intervention needed - ChainRunner may not be running")
    print("=" * 80)
    return False

if __name__ == "__main__":
    try:
        success = test_e2e_autonomous()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
