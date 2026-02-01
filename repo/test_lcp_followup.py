import sys
import os
import json
from pathlib import Path

# Add core to path
sys.path.insert(0, os.getcwd())

from core import storage, models
from core.database import init_db
from core.main import _handle_lcp_followup

def test_lcp():
    init_db()
    
    # Mock job with the exact LLM response found in DB
    job_id = "test-job-" + os.urandom(4).hex()
    result = {
        "type": "lcp", 
        "action": "create_followup_jobs", 
        "ok": True, 
        "commentary": "Debug test", 
        "new_jobs": [
            {"kind": "list_files", "params": {"path": "core/"}}
        ]
    }
    
    mock_job = models.Job(
        id=job_id,
        task_id="test-task",
        payload={"kind": "agent_plan"},
        status="completed",
        result=result,
        created_at="2026-01-26T04:00:00Z",
        updated_at="2026-01-26T04:00:00Z"
    )
    
    print(f"Testing _handle_lcp_followup with job {job_id}...")
    _handle_lcp_followup(mock_job)
    
    # Check if spec was registered
    from core.database import get_db
    with get_db() as conn:
        row = conn.execute("SELECT * FROM chain_specs WHERE root_job_id = ?", (job_id,)).fetchone()
        if row:
            print("✅ SUCCESS: Spec registered!")
            print(f"Spec info: {dict(row)}")
        else:
            print("❌ FAILURE: Spec not found in chain_specs.")

if __name__ == "__main__":
    test_lcp()
