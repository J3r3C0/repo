# repo/core/chain.py
import time
import uuid
import logging
import threading
import json
import os
import tempfile
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any, List

from core import store, models, config
from core.database import get_db

# --- CHAIN INDEX (Simplified) ---
class ChainIndex:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"jobs": {}})

    def _read(self) -> Dict[str, Any]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {"jobs": {}}

    def _write(self, data: Dict[str, Any]):
        fd, tmp = tempfile.mkstemp(prefix="chain_index_", dir=str(self.path.parent))
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, str(self.path))

    def put(self, job_id: str, info: Dict[str, Any]):
        data = self._read()
        data.setdefault("jobs", {})[job_id] = info
        self._write(data)

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._read().get("jobs", {}).get(job_id)

# --- CHAIN MANAGER (Simplified) ---
class ChainManager:
    def __init__(self, chain_dir: Path, index: ChainIndex):
        self.chain_dir = chain_dir
        self.index = index
        self.chain_dir.mkdir(parents=True, exist_ok=True)

    def resolve_chain_spec(self, chain_id: str, spec_id: str, conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
        # Minimal resolution for now (just returns the raw params)
        def _do_resolve(c):
            row = c.execute(
                "SELECT params_json FROM chain_specs WHERE chain_id=? AND spec_id=?",
                (chain_id, spec_id)
            ).fetchone()
            if not row:
                raise ValueError(f"Spec {spec_id} not found in chain {chain_id}")
            params = json.loads(row[0]) if row[0] else {}
            
            # Mark as resolved
            c.execute(
                "UPDATE chain_specs SET resolved=1, resolved_params_json=? WHERE chain_id=? AND spec_id=?",
                (json.dumps(params), chain_id, spec_id)
            )
            return params

        if conn:
            return _do_resolve(conn)
        else:
            with get_db() as c:
                res = _do_resolve(c)
                c.commit()
                return res

# --- CHAIN RUNNER ---
class ChainRunner:
    def __init__(self, poll_interval: float = 1.0):
        self.poll_interval = poll_interval
        self.logger = logging.getLogger("chain_runner")
        
        index_path = config.DATA_DIR / "chain_index.json"
        self.index = ChainIndex(index_path)
        self.manager = ChainManager(config.DATA_DIR / "chains", self.index)
        
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self._thread and self._thread.is_alive(): return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="ChainRunner")
        self._thread.start()
        self.logger.info("[chain_runner] Thread started.")
        self.logger.info("ChainRunner started")

    def stop(self):
        self._stop_event.set()
        if self._thread: self._thread.join(timeout=5)

    def _run(self):
        self.logger.info("[chain_runner] Loop entered.")
        while not self._stop_event.is_set():
            try:
                processed = self.tick()
                if processed == 0:
                    time.sleep(self.poll_interval)
                else:
                    self.logger.info(f"[chain_runner] Processed {processed} specs.")
                    time.sleep(0.1) # Yield to other database users
            except Exception as e:
                self.logger.error(f"[chain_runner] Loop error: {e}", exc_info=True)
                time.sleep(5)

    def tick(self) -> int:
        processed = 0
        with get_db() as conn:
            # 1) List chains needing tick
            cids = store.list_chains_needing_tick(conn, limit=20)
            if not cids: return 0
            
            self.logger.info(f"[chain_runner] Found {len(cids)} chains needing tick: {cids}")
            
            for cid in cids:
                if self._stop_event.is_set(): break
                
                try:
                    conn.execute("BEGIN IMMEDIATE")
                    
                    # 2) Claim next pending spec
                    spec = store.claim_next_pending_spec(conn, cid)
                    
                    if not spec:
                        self.logger.info(f"[chain_runner] No pending specs for chain {cid}, disabling needs_tick.")
                        # No more specs for this chain
                        store.set_chain_needs_tick(conn, cid, False)
                        conn.commit()
                        continue
                    
                    sid = spec["spec_id"]
                    kind = spec["kind"]
                    tid = spec["task_id"]
                    rid = spec["root_job_id"]
                    pid = spec["parent_job_id"]
                    
                    # 3) Resolve spec (Pass conn to avoid deadlock!)
                    params = self.manager.resolve_chain_spec(cid, sid, conn=conn)
                    
                    # 4) Dispatch Job
                    job_id = str(uuid.uuid4())
                    job = models.Job(
                        id=job_id, task_id=tid, status="pending", created_at=store._now_iso(),
                        updated_at=store._now_iso(), payload={
                            "kind": kind, "params": params, 
                            "_chain_hint": {"chain_id": cid, "spec_id": sid, "role": "child"}
                        },
                        idempotency_key=f"spec:{sid}", depends_on=[pid] if pid else []
                    )
                    store.create_job(job, conn=conn)
                    
                    # 5) Mark spec as dispatched
                    store.mark_chain_spec_dispatched(conn, cid, sid, job_id)
                    
                    conn.commit()
                    processed += 1
                except sqlite3.OperationalError as e:
                    if "locked" in str(e):
                        conn.rollback()
                        continue
                    raise
                except Exception as e:
                    self.logger.error(f"[chain_runner] Error ticking chain {cid}: {e}", exc_info=True)
                    conn.rollback()
                
        return processed

# Global instance for app lifecycle
chain_runner = ChainRunner()
