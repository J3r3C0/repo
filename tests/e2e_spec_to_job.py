"""
E2E Test Suite: Spec→Job Pipeline Verification
Standardized for Sheratan Evolution (Modular Core)
"""
import sys
import time
import uuid
import sqlite3
from pathlib import Path
from datetime import datetime

# Adjust path to include repo/
sys.path.insert(0, str(Path(__file__).parent.parent))

from repo.core.database import get_db
from repo.core import store, models

class E2ETestSuite:
    def __init__(self):
        self.log("Initializing E2E Test Suite...")

    def log(self, msg: str):
        print(f"[E2E] {msg}")

    def with_retry(self, fn, max_tries=10, delay=1.0):
        for i in range(max_tries):
            try:
                return fn()
            except sqlite3.OperationalError as e:
                if "locked" in str(e) and i < max_tries - 1:
                    self.log(f"⚠️ Database locked, retrying {i+1}/{max_tries}...")
                    time.sleep(delay)
                    continue
                raise

    def test_spec_to_jobs(self) -> bool:
        """Verified Spec → Jobs Creation (Phase 4 Goal)"""
        self.log("=" * 60)
        self.log("TEST: Spec → Jobs Creation (Modular ChainRunner)")
        self.log("=" * 60)
        
        task_id = f"e2e_task_{uuid.uuid4().hex[:8]}"
        chain_id = f"e2e_chain_{uuid.uuid4().hex[:8]}"
        
        # 1. Create task
        task = models.Task(
            id=task_id,
            mission_id="e2e_test",
            name="E2E Spec Test",
            description="Spec to jobs test",
            kind="test",
            params={},
            created_at=datetime.utcnow().isoformat() + "Z"
        )
        self.with_retry(lambda: store.create_task(task))
        self.log(f"✓ Created task: {task_id}")
        
        # 2. Setup Chain Context and Specs
        with get_db() as conn:
            self.with_retry(lambda: store.ensure_chain_context(conn, chain_id, task_id))
            self.log(f"✓ Created chain context: {chain_id}")
            
            specs = [
                {
                    "spec_id": f"spec1_{uuid.uuid4().hex[:8]}",
                    "kind": "read_file",
                    "params": {"path": "repo/main.py"}
                },
                {
                    "spec_id": f"spec2_{uuid.uuid4().hex[:8]}",
                    "kind": "read_file",
                    "params": {"path": "repo/readme.md"}
                }
            ]
            
            self.with_retry(lambda: store.append_chain_specs(conn, chain_id, task_id, "root", "", specs))
            self.with_retry(lambda: store.set_chain_needs_tick(conn, chain_id, True))
            conn.commit()
            self.log(f"✓ Registered 2 specs, needs_tick=True")
        
        # 3. Wait for ChainRunner to process
        self.log("⏳ Waiting 25s for ChainRunner to create jobs...")
        deadline = time.time() + 25
        jobs_created = False
        
        while time.time() < deadline:
            with get_db() as conn:
                count = conn.execute(
                    "SELECT COUNT(*) FROM jobs WHERE task_id=?", (task_id,)
                ).fetchone()[0]
                
                if count >= 2:
                    self.log(f"✓ ChainRunner created {count} jobs!")
                    jobs_created = True
                    break
            time.sleep(1.0)
        
        if not jobs_created:
            self.log("❌ FAIL: ChainRunner did not create jobs in time.")
            return False
            
        # 4. Wait for Job Completion (Optional but good for smoke)
        self.log("⏳ Waiting 25s for jobs to complete...")
        deadline = time.time() + 25
        
        while time.time() < deadline:
            with get_db() as conn:
                completed = conn.execute(
                    "SELECT COUNT(*) FROM jobs WHERE task_id=? AND status IN ('completed', 'done')",
                    (task_id,)
                ).fetchone()[0]
                
                if completed >= 2:
                    self.log(f"✅ PASS: {completed} jobs processed.")
                    return True
            time.sleep(1.0)
            
        self.log("❌ FAIL: Jobs created but not completed in time.")
        return False

    def run(self):
        try:
            success = self.test_spec_to_jobs()
            return 0 if success else 1
        except Exception as e:
            self.log(f"💥 CRITICAL TEST ERROR: {e}")
            import traceback
            traceback.print_exc()
            return 1

if __name__ == "__main__":
    suite = E2ETestSuite()
    sys.exit(suite.run())
