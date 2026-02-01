import time
from datetime import datetime
from typing import Optional
import os

from hub import storage
from core.config import RobustnessConfig
from hub.orchestrator import SheratanOrchestrator
from hub.metrics_client import record_module_call
import json

def normalize_trace_state(state):
    s = dict(state or {})
    if "context_refs" not in s: s["context_refs"] = []
    if "constraints" not in s or not s["constraints"]:
        s["constraints"] = {"budget_remaining": 100, "risk_level": "low"}
    return s

def normalize_trace_action(action):
    import uuid
    a = dict(action or {})
    if "action_id" not in a: a["action_id"] = str(uuid.uuid4())
    if "type" not in a: a["type"] = "EXECUTE"
    if "mode" not in a: a["mode"] = "execute"
    if "params" not in a: a["params"] = {}
    if "select_score" not in a: a["select_score"] = 1.0
    if "risk_gate" not in a: a["risk_gate"] = True
    return a

def normalize_trace_result(result):
    r = dict(result or {})
    if "status" not in r: r["status"] = "success"
    if "metrics" not in r: r["metrics"] = {}
    if "score" not in r: r["score"] = 1.0
    return r

class Dispatcher:
    """Central dispatcher for Priority Queuing and Rate Limiting. Moved to Hub."""
    def __init__(self, bridge, lcp, orchestrator: Optional[SheratanOrchestrator] = None, rate_limiter=None, audit_logger=None):
        self.bridge = bridge
        self.lcp = lcp
        self.orchestrator = orchestrator
        self.rate_limiter = rate_limiter
        self.audit_logger = audit_logger
        self._running = False

    def start(self):
        if getattr(self, "_running", False):
            return
        self._running = True
        import threading
        self._thread = threading.Thread(target=self._run_loop, name="dispatcher", daemon=True)
        self._thread.start()

    def _run_loop(self):
        while self._running:
            try:
                missions = storage.list_missions()
                for m in missions:
                    if getattr(m, 'status', None) == "planned":
                        m.status = "active"
                        storage.update_mission(m)

                self._dispatch_step()
                self._sync_step()
            except Exception as e:
                print(f"[dispatcher] Error in loop: {e}")
            time.sleep(2)

    def stop(self):
        self._running = False

    def _dispatch_step(self):
        storage.reap_expired_leases()
        all_jobs = storage.list_jobs()
        pending = [j for j in all_jobs if j.status == "pending"]
        if not pending: return

        inflight_count = storage.count_inflight_jobs()
        if inflight_count >= RobustnessConfig.MAX_INFLIGHT:
            return
        
        completed_ids = {j.id for j in all_jobs if j.status == "completed"}
        ready = [j for j in pending if not j.depends_on or all(dep_id in completed_ids for dep_id in j.depends_on)]
        if not ready: return

        priority_map = {"critical": 0, "high": 1, "normal": 2}
        ready.sort(key=lambda j: (priority_map.get(j.priority, 2), j.created_at))
        
        for job in ready:
            source = "default_user"
            if not self.rate_limiter or self.rate_limiter.check_limit(source):
                try:
                    if self.orchestrator:
                        self.orchestrator.dispatch_job(job.id, self.bridge, build_id="hub-v1")
                    else:
                        self.bridge.enqueue_job(job.id)
                    
                    job = storage.get_job(job.id)
                    job.status = "working"
                    job.updated_at = datetime.utcnow().isoformat() + "Z"
                    storage.update_job(job)
                    
                    record_module_call(source="hub.dispatcher", target=f"dispatch.{job.payload.get('kind', 'unknown')}", duration_ms=0, status="ok")
                    
                    if self.audit_logger:
                        self.audit_logger("JOB_DISPATCHED", {"job_id": job.id})
                        
                except Exception as e:
                    print(f"[dispatcher] [FAIL] {job.id[:8]}: {e}")
            else:
                break

    def _sync_step(self):
        working = [j for j in storage.list_jobs() if j.status in ["working", "running"]]
        for job in working:
            try:
                synced = self.bridge.try_sync_result(job.id)
                if synced:
                    if synced.status == "failed":
                        max_retries = RobustnessConfig.RETRY_MAX_ATTEMPTS
                        if synced.retry_count < max_retries:
                            synced.retry_count += 1
                            synced.status = "pending"
                            delay_ms = RobustnessConfig.RETRY_BASE_DELAY_MS * (2 ** (synced.retry_count - 1))
                            from datetime import timedelta
                            synced.next_retry_utc = (datetime.utcnow() + timedelta(milliseconds=delay_ms)).isoformat() + "Z"
                            storage.update_job(synced)
                            continue

                    if synced.status == "completed" and synced.idempotency_key:
                        from hub.result_integrity import compute_result_hash
                        res_hash = compute_result_hash({"ok": True, "status": "completed", "result_id": synced.id})
                        storage.cache_completed_result(synced.id, {"ok": True}, result_hash=res_hash)
            except Exception as e:
                print(f"[dispatcher] Sync failure: {e}")
