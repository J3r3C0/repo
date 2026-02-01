#!/usr/bin/env python3
"""
Direct DB E2E Test - Bypasses API
Tests Mission → Task → Job creation directly via database
"""
import sys
import os
from pathlib import Path

# Add repo to path
sys.path.insert(0, str(Path(__file__).parent / "repo"))

import time
import uuid
from core import models, store

def test_direct_db():
    print("=" * 80)
    print("E2E Test: Direct DB Access (Mission → Task → Job)")
    print("=" * 80)
    
    # Initialize
    print("\n[1/4] Initializing database...")
    store.initialize()
    print("✓ Database initialized")
    
    # Create Mission
    print("\n[2/4] Creating mission...")
    mission = models.Mission(
        id=f"m-e2e-{uuid.uuid4().hex[:8]}",
        title="E2E Autonomy Test",
        description="Testing autonomous follow-up job generation",
        user_id="test-user",
        status="active",
        metadata={"test": True},
        tags=["e2e", "autonomous"]
    )
    store.create_mission(mission)
    print(f"✓ Mission: {mission.id}")
    print(f"  Title: {mission.title}")
    
    # Create Task
    print("\n[3/4] Creating task...")
    task = models.Task(
        id=f"t-e2e-{uuid.uuid4().hex[:8]}",
        mission_id=mission.id,
        name="Planning Phase",
        description="Generate execution plan with follow-up jobs",
        kind="plan",
        params={"objective": "Test LCP follow-up"}
    )
    store.create_task(task)
    print(f"✓ Task: {task.id}")
    print(f"  Mission ID: {task.mission_id}")
    
    # Create Job
    print("\n[4/4] Creating job...")
    job = models.Job(
        id=f"j-e2e-{uuid.uuid4().hex[:8]}",
        task_id=task.id,
        payload={
            "kind": "llm.chat",
            "instruction": "Create a plan with 2 follow-up jobs",
            "context": {"mission_id": mission.id, "task_id": task.id}
        },
        status="pending",
        priority=5
    )
    store.create_job(job)
    print(f"✓ Job: {job.id}")
    print(f"  Task ID: {job.task_id}")
    print(f"  Status: {job.status}")
    
    # Summary
    print("\n" + "=" * 80)
    print("✓ SUCCESS: Created Mission → Task → Job")
    print("=" * 80)
    print(f"Mission ID: {mission.id}")
    print(f"Task ID:    {task.id}")
    print(f"Job ID:     {job.id}")
    print()
    print("Next steps for full autonomy test:")
    print("1. Simulate LCP response with follow-up jobs")
    print("2. Create chain_spec in database")
    print("3. Verify ChainRunner picks up and creates follow-up jobs")
    print("=" * 80)
    
    return mission.id, task.id, job.id

if __name__ == "__main__":
    try:
        mission_id, task_id, job_id = test_direct_db()
        print(f"\n✓ TEST PASSED")
        print(f"\nCreated IDs:")
        print(f"  Mission: {mission_id}")
        print(f"  Task:    {task_id}")
        print(f"  Job:     {job_id}")
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
