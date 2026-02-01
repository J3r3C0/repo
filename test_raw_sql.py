#!/usr/bin/env python3
"""
Ultra-Simple E2E Test - Pure SQL
"""
import sqlite3
import time
import uuid
import json

DB_PATH = "data/sheratan.db"

def test_raw_sql():
    print("=" * 80)
    print("E2E Test: Raw SQL (Mission → Task → Job)")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    
    # IDs
    mission_id = f"m-e2e-{uuid.uuid4().hex[:8]}"
    task_id = f"t-e2e-{uuid.uuid4().hex[:8]}"
    job_id = f"j-e2e-{uuid.uuid4().hex[:8]}"
    ts = time.time()
    
    # Create Mission
    print(f"\n[1/3] Creating mission {mission_id}...")
    conn.execute("""
        INSERT INTO missions (id, title, description, user_id, status, metadata, tags, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (mission_id, "E2E Autonomy Test", "Testing autonomous flow", "test-user", 
          "active", "{}", "[]", ts))
    print(f"✓ Mission created")
    
    # Create Task
    print(f"\n[2/3] Creating task {task_id}...")
    conn.execute("""
        INSERT INTO tasks (id, mission_id, name, description, kind, params, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (task_id, mission_id, "Planning Phase", "Generate plan", "plan", "{}", ts))
    print(f"✓ Task created with mission_id={mission_id}")
    
    # Create Job
    print(f"\n[3/3] Creating job {job_id}...")
    payload = json.dumps({"kind": "llm.chat", "instruction": "Test LCP"})
    conn.execute("""
        INSERT INTO jobs (id, task_id, payload, status, priority, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (job_id, task_id, payload, "pending", 5, ts, ts))
    print(f"✓ Job created with task_id={task_id}")
    
    conn.commit()
    conn.close()
    
    print("\n" + "=" * 80)
    print("✓ SUCCESS: Mission → Task → Job hierarchy created!")
    print("=" * 80)
    print(f"Mission: {mission_id}")
    print(f"Task:    {task_id} (parent={mission_id})")
    print(f"Job:     {job_id} (parent={task_id})")
    print("=" * 80)
    
    return mission_id, task_id, job_id

if __name__ == "__main__":
    try:
        m, t, j = test_raw_sql()
        print(f"\n✓ TEST PASSED\n")
    except Exception as e:
        print(f"\n✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
