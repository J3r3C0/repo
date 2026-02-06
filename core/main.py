from __future__ import annotations

"""
Sheratan Core v2 – Unified API

Missions → Tasks → Jobs
+ WebRelay Bridge (Phase 9: LLM-Worker)
+ LCP Actions (Ledger Capability Protocol)
+ Dispatcher (Autonomous Job Orchestration)
+ ChainRunner (Spec→Job Creation)
"""


def normalize_trace_state(state):
    """Ensure state satisfies decision_trace_v1 schema."""
    s = dict(state or {})
    if "context_refs" not in s: s["context_refs"] = []
    if "constraints" not in s or not s["constraints"]:
        s["constraints"] = {"budget_remaining": 100, "risk_level": "low"}
    return s

def normalize_trace_action(action):
    """Ensure action satisfies decision_trace_v1 schema."""
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
    """Ensure result satisfies decision_trace_v1 schema."""
    r = dict(result or {})
    if "status" not in r: r["status"] = "success"
    if "metrics" not in r: r["metrics"] = {}
    if "score" not in r: r["score"] = 1.0
    return r
import asyncio
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Request
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
import sys
import os
from pathlib import Path

from core.config import BASE_DIR
SHERATAN_ROOT = BASE_DIR

# Force UTF-8 for Windows shell logging
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Add parent directory to sys.path so 'core' module can be imported
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.database import get_db, init_db
from core import models
from core import storage
from core.webrelay_bridge import WebRelayBridge, WebRelaySettings
from core.lcp_actions import LCPActionInterpreter
from core.job_chain_manager import JobChainManager
from core.chain_runner import ChainRunner
from core.metrics_client import record_module_call, measured_call
from core.rate_limiter import RateLimiter
from core.performance_baseline import PerformanceBaselineTracker
from core.self_diagnostics import SelfDiagnosticEngine, DiagnosticConfig
from core.anomaly_detector import AnomalyDetector
from core.gateway_middleware import enforce_gateway, GatewayViolation
from core.attestation import evaluate_attestation, verify_signature
from core.config import RobustnessConfig, BASE_DIR
from core import storage, models, idempotency, result_integrity
from core.idempotency import evaluate_idempotency, IdempotencyDecision, build_idempotency_conflict_detail
from core.result_integrity import verify_or_migrate_hash, IntegrityError, compute_result_hash
import json
import os
import psutil
import socket
import time
import webbrowser
import threading

def _rotate_log(path: Path, max_bytes: int = 10 * 1024 * 1024):
    """Simple log rotation by size capping."""
    try:
        if path.exists() and path.stat().st_size > max_bytes:
            backup = path.with_suffix(".jsonl.bak")
            if backup.exists():
                backup.unlink()
            path.rename(backup)
    except Exception as e:
        print(f"[log] Rotation failed for {path.name}: {e}")

def _audit_log(event: str, details: dict):
    """Standardized Security Audit Logging for Track A2 with rotation."""
    try:
        audit_file = storage.DATA_DIR / "logs" / "hub_security_audit.jsonl"
        audit_file.parent.mkdir(parents=True, exist_ok=True)
        _rotate_log(audit_file)
        entry = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "event": event,
            "details": details
        }
        with audit_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[audit] Failed to write audit log: {e}")

def _alert_log(event: str, details: dict):
    """Standardized Alert Logging for Track A3 with rotation."""
    try:
        alert_file = storage.DATA_DIR / "logs" / "alerts.jsonl"
        alert_file.parent.mkdir(parents=True, exist_ok=True)
        _rotate_log(alert_file)
        entry = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "event": event,
            "details": details
        }
        with alert_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[alert] Failed to write alert log: {e}")

from core.policy_engine import PolicyEngine
policy_engine = PolicyEngine()

from core.health import health_manager
rate_limiter = RateLimiter()
from core.config import CORE_START_TIME

# --- Track V-Mesh: System Control Logic ---
from core.vmesh.stability import StabilityEvaluator
from core.vmesh.complexity import ComplexityTracker
from core.vmesh.sync import SynchronizationLayer
from core.vmesh.service import VMeshService
from core.vmesh.runtime import vmesh_runtime
from core.vmesh.controller import PolicyMode

vmesh_service = VMeshService(
    evaluator=StabilityEvaluator(),
    complexity=ComplexityTracker(),
    sync=SynchronizationLayer()
)

# --- Track B2: Idempotency Metrics (In-Memory) ---
# In-memory counters for performance visibility
IDEMPOTENT_HITS_COUNTER = 0
IDEMPOTENCY_COLLISIONS_COUNTER = 0
INTEGRITY_FAILURES_COUNTER = 0
HASH_WRITES_COUNTER = 0
HASH_MIGRATIONS_COUNTER = 0

class SLOManager:
    """Automated SLO monitoring and alerting (Track C2)."""
    def __init__(self, check_interval_sec: int = 60):
        self.check_interval_sec = check_interval_sec
        self._last_integrity_failures = 0
        self._last_completed_count = 0
        self._last_completed_ts = time.time()
        self._last_job_count = 0
        self._running = False
        self.active_violations = [] # Track current SLO issues

    async def run_loop(self):
        self._running = True
        # Initialize baselines to avoid alert storm at startup
        self._last_integrity_failures = INTEGRITY_FAILURES_COUNTER
        all_jobs = storage.list_jobs()
        self._last_completed_count = len([j for j in all_jobs if j.status == "completed"])
        self._last_job_count = len(all_jobs)
        self._last_completed_ts = time.time()
        
        print(f"[slo] Monitoring loop started (interval={self.check_interval_sec}s)")
        while self._running:
            try:
                await self.evaluate_slos()
            except Exception as e:
                print(f"[slo] Evaluation error: {e}")
            await asyncio.sleep(self.check_interval_sec)

    async def evaluate_slos(self):
        # 1. Queue Depth
        pending = storage.count_pending_jobs()
        max_q = RobustnessConfig.MAX_QUEUE_DEPTH
        if pending >= max_q:
            _alert_log("SLO_QUEUE_CRITICAL", {"pending": pending, "max": max_q, "status": "SATURATED"})
        elif pending >= max_q * 0.8:
            _alert_log("SLO_QUEUE_WARNING", {"pending": pending, "max": max_q, "status": "HIGH_LOAD"})

        # 2. Inflight Saturation
        inflight = storage.count_inflight_jobs()
        max_i = RobustnessConfig.MAX_INFLIGHT
        if inflight >= max_i:
            _alert_log("SLO_INFLIGHT_CRITICAL", {"inflight": inflight, "max": max_i})
        elif inflight >= max_i * 0.8:
            _alert_log("SLO_INFLIGHT_WARNING", {"inflight": inflight, "max": max_i})

        # 3. Integrity
        global INTEGRITY_FAILURES_COUNTER
        if INTEGRITY_FAILURES_COUNTER > self._last_integrity_failures:
            diff = INTEGRITY_FAILURES_COUNTER - self._last_integrity_failures
            _alert_log("SLO_INTEGRITY_FAILURE", {"new_failures": diff, "total": INTEGRITY_FAILURES_COUNTER})
            self._last_integrity_failures = INTEGRITY_FAILURES_COUNTER

        # 4. Stall Detection
        all_jobs = storage.list_jobs()
        completed_count = len([j for j in all_jobs if j.status == "completed"])
        has_pending = pending > 0
        now = time.time()
        
        if completed_count > self._last_completed_count:
            # Progress detected
            self._last_completed_count = completed_count
            self._last_completed_ts = now
        elif has_pending and (now - self._last_completed_ts > 600): # 10 minutes
            # Queue is NOT moving
            _alert_log("SLO_STALL_DETECTED", {
                "last_completion_age_sec": int(now - self._last_completed_ts),
                "pending_jobs": pending
            })

        # 5. Burst Detection
        new_jobs = len(all_jobs) - self._last_job_count
        if new_jobs > 50: # Scale based on your needs
             _alert_log("SLO_BURST_DETECTED", {"count": new_jobs, "interval_sec": self.check_interval_sec})
        self._last_job_count = len(all_jobs)

        # 6. Update Health Summary (Internal)
        self.active_violations = []
        if pending >= max_q: self.active_violations.append("QUEUE_SATURATED")
        if inflight >= max_i: self.active_violations.append("INFLIGHT_SATURATED")
        if has_pending and (now - self._last_completed_ts > 600): self.active_violations.append("STALL_DETECTED")
            
    def stop(self):
        self._running = False

slo_manager = SLOManager(check_interval_sec=60)

class Dispatcher:
    """Central dispatcher for Priority Queuing and Rate Limiting."""
    def __init__(self, bridge: WebRelayBridge, lcp: LCPActionInterpreter):
        self.bridge = bridge
        self.lcp = lcp
        self._running = False

    def start(self):
        if getattr(self, "_running", False):
            print("[dispatcher] start() called but already running")
            return
        self._running = True
        import threading
        self._thread = threading.Thread(target=self._run_loop, name="dispatcher", daemon=True)
        self._thread.start()
        print("[dispatcher] thread launched")

    def _run_loop(self):
        try:
            print("[dispatcher] Central loops started.")
            while self._running:
                try:
                    # Periodic: Auto-activate planned missions (safety catch)
                    missions = storage.list_missions()
                    for m in missions:
                        # Robust check
                        m_status = getattr(m, 'status', None)
                        if m_status == "planned":
                            print(f"[dispatcher] [SYNC] Auto-activating planned mission {m.id[:8]}")
                            m.status = "active"
                            storage.update_mission(m)
                        elif m_status is None:
                            # This should not happen if models are correct, let's log it
                            print(f"[dispatcher] ⚠️ Mission {m.id[:8]} missing status attribute. Type: {type(m)}")

                    self._dispatch_step()
                    self._sync_step()
                except Exception as e:
                    print(f"[dispatcher] Error in loop: {e}")
                time.sleep(2)
            print("[dispatcher] loop exited cleanly")
        except Exception as e:
            import traceback
            print(f"[dispatcher] LOOP CRASH ❌ {repr(e)}")
            traceback.print_exc()
    def stop(self):
        self._running = False
        print("[dispatcher] stop signal sent")
    
    def is_running(self) -> bool:
        t = getattr(self, "_thread", None)
        return bool(getattr(self, "_running", False)) and t is not None and t.is_alive()

    def _dispatch_step(self):
        # 0. Check V-Mesh Policy Mode
        mode = vmesh_runtime.current_mode
        if mode in [PolicyMode.SAFE_MODE, PolicyMode.READONLY]:
            print(f"[dispatcher] [VMESH] {mode.value} active. Dispatching halted.")
            return
        
        # 0. Reap expired leases BEFORE dispatching to free up capacity
        reaped = storage.reap_expired_leases()
        if reaped > 0:
             print(f"[dispatcher] [REAP] Reaped {reaped} expired leases before dispatch.")

        # 1. Get Pending Jobs
        all_jobs = storage.list_jobs()
        pending = [j for j in all_jobs if j.status == "pending"]
        if not pending:
            return

        # 1.5 Backpressure Gate (Inflight)
        inflight_count = storage.count_inflight_jobs()
        if inflight_count >= RobustnessConfig.MAX_INFLIGHT:
            print(f"[dispatcher] [WARN] Inflight saturated ({inflight_count}/{RobustnessConfig.MAX_INFLIGHT}). Deferring dispatch.")
            # Rate limit audit events to avoid spam
            now = time.time()
            if not hasattr(self, "_last_saturated_audit") or now - self._last_saturated_audit > 10:
                _audit_log("BACKPRESSURE_INFLIGHT_SATURATED", {"inflight": inflight_count, "max": RobustnessConfig.MAX_INFLIGHT})
                self._last_saturated_audit = now
            return
        
        print(f"[dispatcher] _dispatch_step: {len(pending)} pending jobs found")

        # 2. Get completed job IDs for dependency checking
        completed_ids = {j.id for j in all_jobs if j.status == "completed"}

        # 3. Filter Dependencies
        ready = []
        for j in pending:
            # Dependencies
            if not j.depends_on or all(dep_id in completed_ids for dep_id in j.depends_on):
                ready.append(j)
        
        if not ready:
            print(f"[dispatcher] No jobs ready after dependency filter (all {len(pending)} have unmet dependencies)")
            return

        # 4. Sort by Priority
        # priority_map: critical=0, high=1, normal=2
        priority_map = {"critical": 0, "high": 1, "normal": 2}
        ready.sort(key=lambda j: (priority_map.get(j.priority, 2), j.created_at))
        
        print(f"[dispatcher] {len(ready)} jobs ready for dispatch")

        # 4. Filter Rate Limits
        # For now, we use a single 'system' source or per-mission-owner
        dispatched_count = 0
        for job in ready:
            source = "default_user" # TODO: Get from mission/task
            if rate_limiter.check_limit(source):
                try:
                    # Phase 1: Try to write the job file/mesh-select
                    self.bridge.enqueue_job(job.id)
                    
                    # Phase 2: Only if successful, move status to working
                    print(f"[dispatcher] [DISPATCH] Dispatched job {job.id[:8]} (priority={job.priority})")
                    job.status = "working"
                    job.updated_at = datetime.utcnow().isoformat() + "Z"
                    storage.update_job(job)
                    dispatched_count += 1
                    
                    # Phase 3: Log general decision trace (always, not just MCTS)
                    try:
                        from core.decision_trace import trace_logger
                        trace_logger.log_node(
                            trace_id=f"dispatch-{job.id}",
                            intent="dispatch_job",
                            build_id=os.getenv("SHERATAN_BUILD_ID", "main-v2"),
                            job_id=job.id,
                            state=normalize_trace_state({
                                "context_refs": [f"job:{job.id}"],  # Required by schema
                                "job_status": "pending→working",
                                "priority": job.priority,
                                "queue_position": ready.index(job) if job in ready else -1
                            }),
                            action=normalize_trace_action({
                                "type": "ROUTE",
                                "mode": "execute",
                                "params": {
                                    "worker_id": job.payload.get("mesh", {}).get("worker_id", "unknown"),
                                    "kind": job.payload.get("kind", "unknown")
                                }
                            }),
                            result=normalize_trace_result({
                                "status": "success",
                                "metrics": {"dispatch_latency_ms": 0}
                            })
                        )
                    except Exception as trace_err:
                        print(f"[dispatcher] Warning: Failed to log dispatch trace: {trace_err}")
                    
                except ValueError as ve:
                    # Orphaned job (missing task/mission) - mark as failed
                    print(f"[dispatcher] [WARN] Orphaned job {job.id[:8]}: {ve}")
                    job.status = "failed"
                    job.result = {"ok": False, "error": f"Orphaned job: {str(ve)}"}
                    job.updated_at = datetime.utcnow().isoformat() + "Z"
                    storage.update_job(job)
                except Exception as e:
                    print(f"[dispatcher] [FAIL] FAILED to dispatch job {job.id[:8]}: {e}")
                    # Job remains in 'pending', will be retried next loop unless fixed
            else:
                # Stop dispatching this batch if source is limited
                print(f"[dispatcher] Rate limit hit for {source}, stopping dispatch")
                break
        
        if dispatched_count == 0:
            print(f"[dispatcher] No jobs dispatched (rate limited or other issue)")

    def _sync_step(self):
        # Check all 'working' jobs for results
        working = [j for j in storage.list_jobs() if j.status in ["working", "running"]]
        for job in working:
            synced = self.bridge.try_sync_result(job.id)
            if synced:
                if synced.status == "failed":
                    # --- STANDARDIZED RETRY POLICY (B1) ---
                    max_retries = RobustnessConfig.RETRY_MAX_ATTEMPTS
                    if synced.retry_count < max_retries:
                        synced.retry_count += 1
                        synced.status = "pending"
                        
                        # Exponential Backoff: base * (2 ^ (attempts-1))
                        # e.g. 500ms, 1000ms, 2000ms, 4000ms, 8000ms
                        delay_ms = RobustnessConfig.RETRY_BASE_DELAY_MS * (2 ** (synced.retry_count - 1))
                        from datetime import timedelta
                        next_retry = datetime.utcnow() + timedelta(milliseconds=delay_ms)
                        synced.next_retry_utc = next_retry.isoformat() + "Z"
                        
                        synced.updated_at = datetime.utcnow().isoformat() + "Z"
                        storage.update_job(synced)
                        
                        _audit_log("RETRY_SCHEDULED", {"job_id": synced.id, "attempts": synced.retry_count, "next_retry": synced.next_retry_utc})
                        print(f"[dispatcher] [RETRY] Job {job.id[:8]} failed. Scheduled for retry {synced.retry_count}/{max_retries} at {synced.next_retry_utc}")
                        continue
                    else:
                        _audit_log("RETRY_EXHAUSTED", {"job_id": synced.id, "attempts": synced.retry_count})
                        print(f"[dispatcher] [FAIL] Job {job.id[:8]} failed after {max_retries} attempts.")
                
                # Final result (success or max failure)
                print(f"[dispatcher] ✓ Job {job.id[:8]} finished with status: {synced.status}")
                
                # --- IDEMPOTENCY COMPLETION HOOK (B2) ---
                if synced.status == "completed" and synced.idempotency_key:
                    # Track B3: Compute Hash
                    result_obj = {
                        "ok": True,
                        "status": "completed",
                        "result_id": synced.id # or specific result identifier if available
                    }
                    res_hash = compute_result_hash(result_obj)
                    storage.cache_completed_result(synced.id, result_obj, result_hash=res_hash, result_hash_alg="sha256")
                    
                    # Update audit/metrics (B3)
                    global HASH_WRITES_COUNTER
                    HASH_WRITES_COUNTER += 1
                    _audit_log("RESULT_HASH_COMPUTED", {"job_id": synced.id, "hash_prefix": res_hash[:12]})
                
                _handle_lcp_followup(synced)


# --- PHASE A: State Machine ---
from core.state_machine import SystemStateMachine, SystemState
state_machine = SystemStateMachine(
    load_path="runtime/system_state.json",
    log_path="logs/state_transitions.jsonl"
)

# --- PHASE 1: Performance Baseline Tracker ---
baseline_tracker = PerformanceBaselineTracker(
    runtime_dir="runtime",
    filename="performance_baselines.json",
)

# --- PHASE 2: Anomaly Detector ---
anomaly_detector = AnomalyDetector(max_anomalies=500)

# --- PHASE 3: Self-Diagnostic Engine ---
diagnostic_engine = SelfDiagnosticEngine(
    state_machine=state_machine,
    baseline_tracker=baseline_tracker,
    anomaly_detector=anomaly_detector,
    config=DiagnosticConfig(
        check_interval_sec=300,  # 5 minutes
        persist_interval_sec=60,
        reflective_enabled=False,  # conservative for now
    ),
)

# --- ChainRunner: Spec→Job Creation ---
chain_runner = ChainRunner(
    storage_mod=storage,
    poll_interval_sec=1.0,
    lease_seconds=120
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 0. Initialize Database Schema (FIRST - before anything else)
    print("[database] Initializing schema...")
    init_db()
    print("[database] Schema initialization complete [OK]")
    
    # 0.1 Reap expired leases (Safety cleanup)
    reaped = storage.reap_expired_leases()
    if reaped > 0:
        print(f"[storage] Reaped {reaped} expired leases at startup.")
    
    # 0.2 Start V-Mesh Service
    vmesh_service.register_source("ledger_conflicts", lambda: INTEGRITY_FAILURES_COUNTER)
    vmesh_service.register_source("latency", lambda: diagnostic_engine.get_latest_report().get("avg_job_latency_ms", 200.0) or 200.0)
    await vmesh_service.start()
    print("[vmesh] Control logic initialized")
    
    # 1. Initialize State Machine
    state_machine.load_or_init()
    print(f"[state] System initialized in state: {state_machine.snapshot().state}")
    
    # 2. Initialize Performance Baselines
    baseline_tracker.persist(recompute=True)
    print(f"[baseline] Performance baselines initialized")
    
    # 3. Start Self-Diagnostic Engine
    diagnostic_engine.start()
    print(f"[diagnostic] Self-diagnostic engine started")
    
    # 3.5. Register transition hooks
    state_machine.register_hook(baseline_tracker.on_state_transition)
    print(f"[state] Registered baseline tracker transition hook")
    
    # 3.6. Wire anomaly detector to diagnostic engine
    anomaly_detector.set_reflective_trigger(diagnostic_engine.enter_reflective_mode)
    print(f"[anomaly] Wired anomaly detector to diagnostic engine for REFLECTIVE auto-trigger")
    
    # 4. Start Dispatcher (Legacy)
    try:
        import traceback
        print("[dispatcher] starting ...")
        dispatcher.start()
        print(f"[dispatcher] is_running={dispatcher.is_running()}")
        print("[dispatcher] started [OK]")
    except Exception as e:
        print(f"[dispatcher] FAILED TO START [FAIL] {repr(e)}")
        traceback.print_exc()
        try:
            state_machine.transition(
                SystemState.DEGRADED,
                reason="Dispatcher failed to start",
                actor="core",
                meta={"error": repr(e)},
            )
        except Exception:
            pass
    
    # 5. Start Chain Runner (Spec→Job Creation)
    try:
        print("[chain_runner] starting ...")
        chain_runner.start()
        print("[chain_runner] started [OK]")
    except Exception as e:
        print(f"[chain_runner] FAILED TO START [FAIL] {repr(e)}")
        import traceback
        traceback.print_exc()
    
    # 5.1 Start SLO Monitoring Task
    slo_task = asyncio.create_task(slo_manager.run_loop())
    
    # 4. Transition to OPERATIONAL if health checks pass
    try:
        # Quick health check
        health = await health_manager.evaluate_full_health()
        if health["overall"] == "operational":
            state_machine.transition(
                SystemState.OPERATIONAL,
                reason="All core services started successfully",
                meta={"services": health["services"]}
            )
        else:
            state_machine.transition(
                SystemState.DEGRADED,
                reason="System health check failed at startup",
                meta={"services": health["services"], "critical_down": health["critical_down"]}
            )
    except Exception as e:
        print(f"[state] Warning: Could not evaluate health at startup: {e}")
    
    yield
    
    # Clean up
    try:
        vmesh_service.stop()
        dispatcher.stop()
        chain_runner.stop()
        slo_manager.stop()
        if 'slo_task' in locals():
            slo_task.cancel()
        diagnostic_engine.stop()
        print("[core] all services stopped")
    except Exception as e:
        print(f"[core] warning during cleanup: {e}")
    
    baseline_tracker.persist(recompute=True)
    print(f"[baseline] Performance baselines persisted on shutdown")
    
    state_machine.transition(
        SystemState.PAUSED,
        reason="System shutdown complete",
        actor="system"
    )

# ------------------------------------------------------------------------------
# APP INITIALISIERUNG
# ------------------------------------------------------------------------------

app = FastAPI(
    title="Sheratan Core v2",
    description="Mission/Task/Job orchestration kernel with WebRelay & LCP",
    version="0.3.0",
    lifespan=lifespan
)

# CORS erlauben – für HUD & externe Tools
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # später einschränken falls nötig
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static Dashboard (Track D)
dist_dir = BASE_DIR / "external" / "dashboard" / "dist"

@app.get("/ui", include_in_schema=False)
@app.get("/ui/{path:path}", include_in_schema=False)
async def serve_dashboard(path: str = ""):
    """Serve the React dashboard with SPA fallback (Track D)."""
    if not dist_dir.exists():
        return JSONResponse({"error": f"Dashboard build not found at {dist_dir}. Please ensure it is bundled or built."}, status_code=404)
    
    file_path = dist_dir / path
    if path and file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    
    # SPA Fallback: Serve index.html for all other /ui routes
    index_file = dist_dir / "index.html"
    if not index_file.exists():
        return JSONResponse({"error": "index.html not found in dist"}, status_code=404)
    return FileResponse(index_file)

# Keep legacy static mount for other internal files
_this_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=str(_this_dir), html=True), name="static")

# --- WHY-API (Stage 5: Explainability) ---
from core.why_api import router as why_router
app.include_router(why_router, prefix="/api/why")
# -----------------------------------------

# --- V-Mesh Monitoring (Control Plane) ---
@app.get("/api/vmesh/status")
def get_vmesh_status():
    """Returns the current V-Mesh policy mode and stability metrics."""
    return {
        "mode": vmesh_runtime.current_mode.value,
        "stability_s": vmesh_runtime.stability_s,
        "sync_score": vmesh_runtime.sync_score,
        "last_update": datetime.fromtimestamp(vmesh_runtime.last_update_ts, tz=timezone.utc).isoformat() if vmesh_runtime.last_update_ts else None,
        "control_status": vmesh_service.controller.get_control_status()
    }

# --- MESH ARBITRAGE EXCEPTION HANDLING ---
# Import PaymentRequiredError from the mesh package
try:
    from mesh.registry.client import PaymentRequiredError
    
    @app.exception_handler(PaymentRequiredError)
    async def payment_required_handler(request, exc: PaymentRequiredError):
        return JSONResponse(
            status_code=402,
            content=exc.to_json()
        )
except ImportError:
    # If mesh package is not available, we don't add the handler
    pass

# --- GATEWAY VIOLATION EXCEPTION HANDLING ---
@app.exception_handler(GatewayViolation)
async def gateway_violation_handler(request, exc: GatewayViolation):
    """Handle gateway enforcement violations with detailed gate reports."""
    return JSONResponse(
        status_code=403,
        content=exc.to_dict()
    )
# ------------------------------------------

# ------------------------------------------------------------------------------
# INITIALISIERUNG DER BRIDGE & LCP-ACTIONS
# ------------------------------------------------------------------------------

relay_settings = WebRelaySettings(
    relay_out_dir=BASE_DIR / "external" / "webrelay" / "runtime" / "narrative",
    relay_in_dir=BASE_DIR / "external" / "webrelay" / "runtime" / "output",
    session_prefix="core_v2"
)

bridge = WebRelayBridge(relay_settings)
lcp = LCPActionInterpreter(bridge=bridge)

# Phase 9: Initialize JobChainManager for LCP Job Chaining
from core.chain_index import ChainIndex
chain_index_path = storage.DATA_DIR / "chain_index.json"
chain_dir = storage.DATA_DIR / "chains"
chain_index = ChainIndex(str(chain_index_path))
chain_manager = JobChainManager(
    chain_dir=str(chain_dir),
    chain_index=chain_index,
    storage=storage,
    logger=None,  # Use print() for now
    agent_plan_kind="agent_plan",
)

# Dispatcher instantiation (BASIS FOR ALL AUTOMATION)
dispatcher = Dispatcher(bridge, lcp)
# dispatcher.start() # Now handled via lifespan


# ------------------------------------------------------------------------------
# MISSIONS – CRUD
# ------------------------------------------------------------------------------

@app.post("/api/missions", response_model=models.Mission)
def create_mission(mission_create: models.MissionCreate):
    if not check_vmesh_action("write"):
        raise HTTPException(status_code=503, detail="V-Mesh Policy: Mutation restricted (SAFE_MODE/READONLY)")
    
    mission = models.Mission.from_create(mission_create)
    # Ensure mission starts as active for immediate orchestration
    mission.status = "active"
    storage.create_mission(mission)
    
    # Initialize mission documentation files
    try:
        mission_dir = storage.DATA_DIR / "missions"
        mission_dir.mkdir(parents=True, exist_ok=True)
        
        plan_file = mission_dir / f"{mission.id}_plan.md"
        progress_file = mission_dir / f"{mission.id}_progress.md"
        
        # Initial plan content
        plan_content = f"# Mission Plan: {mission.title}\n\n## Objective\n{mission.description}\n\n## Status\nActive\n"
        plan_file.write_text(plan_content, encoding="utf-8")
        
        # Initial progress content
        progress_content = f"# Mission Progress: {mission.title}\n\n## Log\n[Init] Mission created at {mission.created_at}\n"
        progress_file.write_text(progress_content, encoding="utf-8")
        
        print(f"[api] Created mission files and ACTIVATED mission {mission.id[:8]}")
    except Exception as e:
        print(f"[api] Warning: Could not create mission files: {e}")

    return mission


@app.get("/api/missions", response_model=List[models.Mission])
def list_missions():
    return storage.list_missions()


@app.get("/api/missions/{mission_id}", response_model=models.Mission)
def get_mission(mission_id: str):
    m = storage.get_mission(mission_id)
    if m is None:
        raise HTTPException(404, "Mission not found")
    return m


@app.put("/api/missions/{mission_id}", response_model=models.Mission)
def update_mission(mission_id: str, mission: models.Mission):
    if not check_vmesh_action("write"):
        raise HTTPException(status_code=503, detail="V-Mesh Policy: Mutation restricted (SAFE_MODE/READONLY)")
    
    m = storage.get_mission(mission_id)
    if m is None:
        raise HTTPException(404, "Mission not found")
    
    # Ensure ID consistency
    mission.id = mission_id
    storage.update_mission(mission)
    return mission


@app.delete("/api/missions/{mission_id}")
def delete_mission(mission_id: str):
    """Delete a mission and all its related tasks and jobs."""
    if not check_vmesh_action("write"):
        raise HTTPException(status_code=503, detail="V-Mesh Policy: Mutation restricted (SAFE_MODE/READONLY)")
    
    success = storage.delete_mission(mission_id)
    if not success:
        raise HTTPException(404, "Mission not found")
    return {"ok": True, "deleted": mission_id}

@app.get("/api/missions/{mission_id}/chains")
def get_mission_chains(mission_id: str):
    """Retrieve all autonomous chains associated with a mission."""
    with get_db() as conn:
        return storage.list_chains_by_mission(conn, mission_id)

@app.get("/api/chains/{chain_id}/context")
def get_chain_context(chain_id: str):
    """Retrieve the context and artifacts for a specific autonomous chain."""
    with get_db() as conn:
        ctx = storage.get_chain_context(conn, chain_id)
        if not ctx:
            raise HTTPException(status_code=404, detail="Chain context not found")
        return ctx


# ------------------------------------------------------------------------------
# TASKS – CRUD
# ------------------------------------------------------------------------------

@app.post("/api/missions/{mission_id}/tasks", response_model=models.Task)
def create_task_for_mission(mission_id: str, task_create: models.TaskCreate):
    if not check_vmesh_action("write"):
        raise HTTPException(status_code=503, detail="V-Mesh Policy: Mutation restricted (SAFE_MODE/READONLY)")
    
    m = storage.get_mission(mission_id)
    if m is None:
        raise HTTPException(404, "Mission not found")

    task = models.Task.from_create(mission_id, task_create)
    storage.create_task(task)
    return task


@app.get("/api/tasks", response_model=List[models.Task])
def list_tasks():
    return storage.list_tasks()


@app.get("/api/tasks/{task_id}", response_model=models.Task)
def get_task(task_id: str):
    t = storage.get_task(task_id)
    if t is None:
        raise HTTPException(404, "Task not found")
    return t


# ------------------------------------------------------------------------------
# JOBS – CRUD & DISPATCH
# ------------------------------------------------------------------------------

@app.post("/api/tasks/{task_id}/jobs", response_model=models.Job)
def create_job_for_task(task_id: str, job_create: models.JobCreate):
    if not check_vmesh_action("write"):
        raise HTTPException(status_code=503, detail="V-Mesh Policy: Mutation restricted (SAFE_MODE/READONLY)")
    
    t = storage.get_task(task_id)
    if t is None:
        raise HTTPException(404, "Task not found")

    # --- BACKPRESSURE GATE (Queue Depth) ---
    pending_count = storage.count_pending_jobs()
    if pending_count >= RobustnessConfig.MAX_QUEUE_DEPTH:
        _audit_log("BACKPRESSURE_QUEUE_LIMIT", {"queue_depth": pending_count, "max": RobustnessConfig.MAX_QUEUE_DEPTH})
        # Note: Brief suggests 429 for submit
        raise HTTPException(status_code=429, detail={"ok": False, "error": "backpressure", "queue_depth": pending_count, "max": RobustnessConfig.MAX_QUEUE_DEPTH})
    
    # --- IDEMPOTENCY GATE (G7) (B2) ---
    decision = evaluate_idempotency(
        storage, 
        idempotency_key=job_create.idempotency_key, 
        payload=job_create.payload
    )
    
    if decision.action == "REJECT":
        global IDEMPOTENCY_COLLISIONS_COUNTER
        IDEMPOTENCY_COLLISIONS_COUNTER += 1
        record_module_call(source="idempotency", target="idempotency_collision_1m", duration_ms=0)
        
        _audit_log("IDEMPOTENCY_KEY_COLLISION", {
            "key": job_create.idempotency_key,
            "existing_job_id": decision.job_id,
            "reason": decision.reason
        })
        raise HTTPException(
            status_code=409, 
            detail=build_idempotency_conflict_detail(
                job_create.idempotency_key,
                existing_job_id=decision.job_id,
                existing_hash_prefix=decision.reason, # Using reason as we don't store full hash in decision object yet or need it
                new_hash_prefix=decision.payload_hash[:8] if decision.payload_hash else ""
            )
        )
    
    if decision.action == "RETURN_EXISTING":
        existing_job = storage.get_job(decision.job_id)
        if existing_job:
            global IDEMPOTENT_HITS_COUNTER
            IDEMPOTENT_HITS_COUNTER += 1
            record_module_call(source="idempotency", target="idempotency_hit_1m", duration_ms=0)
            
            _audit_log("IDEMPOTENT_HIT", {"job_id": existing_job.id, "key": job_create.idempotency_key})
            # Return existing job directly
            # We add a meta flag to indicate it was deduplicated
            # Result Integrity Check (Track B3)
            if decision.cached_result:
                try:
                    def persist_integrity(h, a):
                        global HASH_MIGRATIONS_COUNTER
                        HASH_MIGRATIONS_COUNTER += 1
                        storage.update_job_integrity(existing_job.id, h, a)
                        _audit_log("RESULT_HASH_MIGRATED", {"job_id": existing_job.id, "hash_prefix": h[:12]})
                    
                    verify_or_migrate_hash(
                        result_obj=decision.cached_result,
                        expected_hash=existing_job.result_hash,
                        alg=existing_job.result_hash_alg or "sha256",
                        persist_hash=persist_integrity
                    )
                except IntegrityError as e:
                    global INTEGRITY_FAILURES_COUNTER
                    INTEGRITY_FAILURES_COUNTER += 1
                    _audit_log("RESULT_INTEGRITY_FAIL", {
                        "job_id": existing_job.id,
                        "expected": existing_job.result_hash,
                        "error": str(e)
                    })
                    raise HTTPException(403, detail="Result integrity verification failed. Data may be tampered.")

            res = existing_job.model_dump()
            res["idempotent"] = True
            if decision.cached_result:
                res["cached_result"] = decision.cached_result
            return res

    # --- ALLOW_NEW ---
    job = models.Job.from_create(task_id, job_create)
    job.idempotency_hash = decision.payload_hash
    
    # --- GATEWAY ENFORCEMENT (G0-G4) ---
    # Convert job to dict for gate validation
    job_dict = job.model_dump()
    
    try:
        gate_result = enforce_gateway(job_dict)
        print(f"[gateway] Job {job.id[:8]}: {gate_result['overall_status']} (allowed={gate_result['allowed']})")
        
        # Store gate result in job metadata
        if not job.meta:
            job.meta = {}
        job.meta["gateway_enforcement"] = {
            "overall_status": gate_result["overall_status"],
            "enforcement_mode": gate_result["enforcement_mode"],
            "allowed": gate_result["allowed"],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except GatewayViolation as gv:
        # Gateway violation will be handled by exception handler
        # This will return 403 with detailed gate reports
        raise
    # --- END GATEWAY ENFORCEMENT ---
    
    storage.create_job(job)
    return job


@app.get("/api/jobs", response_model=List[models.Job])
def list_jobs():
    return storage.list_jobs()


@app.get("/api/jobs/{job_id}", response_model=models.Job)
def get_job(job_id: str):
    j = storage.get_job(job_id)
    if j is None:
        raise HTTPException(404, "Job not found")
    return j


@app.put("/api/jobs/{job_id}", response_model=models.Job)
def update_job(job_id: str, job: models.Job):
    if not check_vmesh_action("write"):
        raise HTTPException(status_code=503, detail="V-Mesh Policy: Mutation restricted (SAFE_MODE/READONLY)")
    
    j = storage.get_job(job_id)
    if j is None:
        raise HTTPException(404, "Job not found")
    
    # Ensure ID consistency
    job.id = job_id
    storage.update_job(job)
    return job


# ------------------------------------------------------------------------------
# JOB → WORKER DISPATCH
# ------------------------------------------------------------------------------

@app.post("/api/jobs/{job_id}/dispatch")
def dispatch_job(job_id: str):
    """
    Manually triggers dispatch (legacy/forced).
    Now mostly handled by central Dispatcher.
    """
    if not check_vmesh_action("write"):
        raise HTTPException(status_code=503, detail="V-Mesh Policy: Mutation restricted (SAFE_MODE/READONLY)")
    
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    
    # Just set status to pending if it's not already
    if job.status != "working":
        job.status = "pending"
        storage.update_job(job)
    
    return {"status": "queued", "job_id": job_id}


# ------------------------------------------------------------------------------
# JOB → RESULT SYNC + LCP FOLLOWUP
# ------------------------------------------------------------------------------

@app.post("/api/jobs/{job_id}/sync", response_model=models.Job)
async def sync_job(job_id: str, request: Request):
    """
    Unified Sync Endpoint:
    1. Tries to read from bridge (file-based)
    2. Fallback to POST body if provided (for tests/overrides)
    """
    payload = None
    try:
        # We use await request.json() to get the POST body
        body = await request.json()
        if body:
            payload = body
    except:
        # No valid JSON body, ignore
        pass

    # 1) Try bridge first
    job = bridge.try_sync_result(job_id)
    
    # 2) Fallback to payload if bridge has no result
    if job is None and payload:
        job = storage.get_job(job_id)
        if job:
            if "status" in payload: job.status = payload["status"]
            if "result" in payload: job.result = payload["result"]
            job.updated_at = datetime.utcnow().isoformat() + "Z"
            # We don't call storage.update_job yet, because the main logic below does it
    
    if job is None:
        # Worker hat noch nichts geliefert - return current job status instead of 404
        current_job = storage.get_job(job_id)
        if current_job is None:
            # Job not in storage
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=202,
                content={"job_id": job_id, "status": "processing", "message": "Job not found in storage, result not ready"}
            )
        # Return 222 Accepted - result not ready yet
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=202,
            content=current_job.model_dump()
        )

    job_id = job.id # Ensure we use the correct ID string
    
    # 2) Worker-Latenz ermitteln (Job-Erstellung → Result Sync)
    worker_latency_ms = 0.0
    try:
        # job.created_at ist bereits ISO-String, z.B. "2025-12-08T12:34:56.123456Z"
        created = datetime.fromisoformat(job.created_at.replace("Z", ""))
        now = datetime.utcnow()
        worker_latency_ms = (now - created).total_seconds() * 1000.0
    except Exception:
        # Wenn irgendwas schiefgeht, ist das nur Monitoring – Core läuft weiter
        pass

    # --- GENERAL DECISION TRACE (ALWAYS) ---
    try:
        from core.decision_trace import trace_logger
        trace_logger.log_node(
            trace_id=f"complete-{job_id}",
            intent="complete_job",
            build_id=os.getenv("SHERATAN_BUILD_ID", "main-v2"),
            job_id=job_id,
            state=normalize_trace_state({
                "context_refs": [f"job:{job_id}"],  # Required by schema
                "job_status": f"working→{job.status}",
                "retry_count": job.retry_count,
                "has_result": job.result is not None
            }),
            action=normalize_trace_action({
                "type": "EXECUTE",
                "mode": "execute",
                "params": {
                    "kind": job.payload.get("kind", "unknown") if isinstance(job.payload, dict) else "unknown"
                }
            }),
            result=normalize_trace_result({
                "status": "success" if job.status == "completed" else "failed",
                "metrics": {
                    "worker_latency_ms": worker_latency_ms,
                    "retry_count": job.retry_count
                },
                "score": 1.0 # Default for non-MCTS sync
            })
        )
    except Exception as trace_err:
        print(f"[sync] Warning: Failed to log completion trace: {trace_err}")

    # --- MCTS LOGGING (CONDITIONAL) ---
    mcts_trace = job.payload.get("mcts_trace")
    if mcts_trace:
        try:
            from core.scoring import compute_score_v1
            from core.mcts_light import mcts
            from core.decision_trace import trace_logger
            
            # 1. Compute Score
            success = 1.0 if job.status == "completed" else 0.0
            # Heuristics for quality/reliability/risk for now
            quality = job.result.get("quality", 1.0) if job.result else 1.0
            reliability = 1.0 if job.retry_count == 0 else (1.0 / (job.retry_count + 1))
            
            # Get metrics from result if available
            metrics = job.result.get("metrics", {})
            latency_ms = metrics.get("latency_ms", worker_latency_ms)
            cost = metrics.get("cost", job.payload.get("mesh", {}).get("cost", 0))
            tokens = metrics.get("tokens", 0)
            risk = metrics.get("risk", 0.0)
            
            score_bd = compute_score_v1(
                success=success,
                quality=quality,
                reliability=reliability,
                latency_ms=latency_ms,
                cost=cost,
                risk=risk
            )
            
            # 2. Update Policy
            chosen_id = mcts_trace.get("chosen_action_id")
            chosen_action = next((c for c in mcts_trace.get("candidates", []) if c.get("action_id") == chosen_id), None)
            if chosen_action:
                mcts.update_policy(
                    intent=mcts_trace["intent"],
                    action_key=chosen_action["action_key"],
                    score=score_bd["score"]
                )
            
            # 3. Log Trace Node
            trace_logger.log_node(
                trace_id=mcts_trace["trace_id"],
                intent=mcts_trace["intent"],
                build_id=mcts_trace.get("build_id", "main-v2"),
                job_id=job_id,
                state=normalize_trace_state({
                    "context_refs": [f"job:{job_id}", f"chain:{job.payload.get('_chain_hint', {}).get('chain_id')}"],
                    "constraints": {"budget_remaining": 100, "risk_level": "low"}
                }),
                action=normalize_trace_action(chosen_action),
                result=normalize_trace_result({
                    "status": "success" if job.status == "completed" else "failed",
                    "metrics": {
                        "latency_ms": latency_ms,
                        "cost": cost,
                        "tokens": tokens,
                        "retries": job.retry_count,
                        "risk": risk,
                        "quality": quality
                    },
                    "score": score_bd["score"]
                })
            )
        except Exception as te:
            print(f"[main] Warning: MCTS logging failed: {te}")
    # ------------------

    record_module_call(
        source="webrelay_worker",
        target="core_v2.api.sync_job",
        duration_ms=worker_latency_ms,
        status="ok" if job.status != "failed" else "error",
        correlation_id=f"job:{job_id}",
    )

    # 3) Phase 10.1: Chain Context + Specs Handling (Thin Sync)
    # If job is completed, cache result for idempotency (G7 follow-up)
    if job.status == "completed" and job.result:
        # Track B3: Compute Hash
        res_hash = compute_result_hash(job.result)
        storage.cache_completed_result(job.id, job.result, result_hash=res_hash, result_hash_alg="sha256")
        
        # Audit & Metrics
        global HASH_WRITES_COUNTER
        HASH_WRITES_COUNTER += 1
        _audit_log("RESULT_HASH_COMPUTED", {"job_id": job.id, "hash_prefix": res_hash[:12]})
        
        # Update local job object too so subsequent filters see it
        job.result_hash = res_hash
        job.result_hash_alg = "sha256"
        
    storage.update_job(job)
        
    _handle_lcp_followup(job)

    # Job ist bereits von bridge.try_sync_result() aktualisiert
    return job

def _handle_lcp_followup(job: models.Job):
    """Unified LCP/Phase 10 follow-up logic."""
    if not job.result or not isinstance(job.result, dict):
        return

    # DEBUG: Log entry
    with open("lcp_debug.log", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now()}] _handle_lcp_followup called for job {job.id}\n")

    from core.lcp_actions import parse_lcp
    from core.context_updaters import update_context_from_job_result
    
    job_id = job.id
    
    # Try to parse LCP envelope
    followup, final = parse_lcp(job.result, default_chain_id=job_id)
    
    # Determine chain_id
    task = storage.get_task(job.task_id)
    chain_id = task.params.get("chain_id") or job_id if task else job_id

    # Update chain context from job result (e.g. store file_list after walk_tree)
    with get_db() as conn:
        # Ensure context exists
        storage.ensure_chain_context(conn, chain_id, job.task_id)
        
        # Update artifacts (file_list, file_blobs, etc)
        artifact_key = update_context_from_job_result(
            conn,
            chain_id=chain_id,
            job_kind=job.payload.get("kind") if isinstance(job.payload, dict) else "unknown",
            job_id=job_id,
            result=job.result,
            set_chain_artifact_fn=storage.set_chain_artifact
        )
        if artifact_key:
            print(f"[sync] Updated artifact '{artifact_key}' for chain {chain_id[:12]}")

        # [RECURSIVE LOOP]
        # If this job was created from a chain_spec, mark that spec as done
        spec_id = job.payload.get("_chain_hint", {}).get("spec_id")
        if spec_id:
            storage.mark_chain_spec_done(conn, chain_id, spec_id, ok=(job.status == "completed"))
            # Trigger runner to check for batch status
            storage.set_chain_needs_tick(conn, chain_id, True)
            print(f"[sync] Marked spec {spec_id[:8]} as done, triggered chain tick.")

    if followup or final:
        print(f"[sync] LCP envelope detected for job {job_id[:12]}...")
        with open("lcp_debug.log", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] LCP ENVELOPE DETECTED for job {job_id}\n")
        
        # Ensure chain exists in manager (creates file if needed)
        chain_manager.ensure_chain(chain_id=chain_id, root_job_id=job_id)
        
        if followup:
            # [ONE TASK PER TURN MODEL]
            # Create a NEW Task for this action turn
            import uuid
            
            # Find turn number
            existing_tasks = []
            if task:
                with get_db() as conn:
                    existing_tasks = conn.execute(
                        "SELECT id FROM tasks WHERE mission_id = ?", 
                        (task.mission_id,)
                    ).fetchall()
            
            turn_num = (len(existing_tasks) // 2) + 1  # Logic: PlanTask, ActionTask, Plan, Action...
            new_task_id = str(uuid.uuid4())
            new_task_name = f"Step {turn_num}: Action Phase"
            
            if task:
                new_task = models.Task(
                    id=new_task_id,
                    mission_id=task.mission_id,
                    name=new_task_name,
                    description=f"Follow-up actions proposed by LLM in job {job_id[:8]}",
                    kind="action_phase",
                    params={"parent_job_id": job_id, "chain_id": chain_id, "turn": turn_num},
                    created_at=datetime.utcnow().isoformat() + "Z"
                )
                storage.create_task(new_task)
                print(f"[sync] Created NEW Task {new_task_id[:8]} '{new_task_name}' for follow-ups")
            
            target_task_id = new_task_id if task else job.task_id

            # Register follow-up SPECS (not jobs!)
            print(f"[sync] Registering {len(followup.jobs)} followup specs...")
            chain_manager.register_followup_specs(
                chain_id=chain_id,
                task_id=target_task_id,
                root_job_id=job.payload.get("root_job_id") or job_id,
                parent_llm_job_id=job_id,
                job_specs=followup.jobs
            )
            with open("lcp_debug.log", "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now()}] REGISTERED {len(followup.jobs)} followup specs for chain {chain_id}\n")
                
        if final:
            # Mark chain as completed
            print(f"[sync] Final answer received for chain {chain_id[:12]}")
            with get_db() as conn:
                storage.set_chain_state(conn, chain_id, "completed")



# ------------------------------------------------------------------------------
# MESH & LEDGER – MONITORING
# ------------------------------------------------------------------------------

@app.get("/api/mesh/workers")
def list_mesh_workers():
    """Returns all workers registered in the Mesh Registry. Reloads from disk."""
    try:
        if not hasattr(bridge, 'registry') or not bridge.registry:
            return []
        
        # Reload from disk to see workers that registered after Core started
        bridge.registry.load()
        
        return [w.model_dump() for w in bridge.registry.workers.values()]
    except Exception as e:
        print(f"[api] Error listing workers: {e}")
        return []

@app.get("/api/mesh/ledger/{user_id}")
def get_user_balance(user_id: str):
    """Returns the balance and recent transfers for a user."""
    try:
        if not hasattr(bridge, 'ledger') or not bridge.ledger:
            return {"balance": 0, "transfers": []}
            
        client = bridge.ledger
        balance = client.get_balance(user_id)
        # Load transfers from the store directly for monitoring
        transfers = []
        if hasattr(client, 'store') and client.store:
            raw_transfers = getattr(client.store, 'transfers', [])
            transfers = [t for t in raw_transfers if t.get("from") == user_id or t.get("to") == user_id]
            
        return {
            "user_id": user_id,
            "balance": balance,
            "transfers": transfers[-20:] # Last 20
        }
    except Exception as e:
        print(f"[api] Error getting balance for {user_id}: {e}")
        return {"balance": 0, "transfers": [], "error": str(e)}

@app.post("/api/hosts/heartbeat")
async def host_heartbeat(payload: dict):
    """
    Receives status from hosts and updates the registry/mesh state.
    Track A2: Evaluates node attestation signals.
    """
    host_id = payload.get("host_id") or payload.get("node_id") or payload.get("name")
    if not host_id:
        return {"ok": False, "error": "missing_host_id"}
        
    status = payload.get("status", "online")
    incoming_att = payload.get("attestation")
    now_utc_str = datetime.utcnow().isoformat() + "Z"
    
    # 1. Load existing host record
    host_record = storage.get_host(host_id) or {"node_id": host_id, "health": "GREEN", "attestation": {}}
    
    # 1. Identity Verification (Track A4 - Ed25519 TOFU)
    incoming_sig = payload.get("signature")
    incoming_pubkey = payload.get("public_key")
    
    stored_pubkey = host_record.get("public_key")
    identity_status = "VALID" # Default for legacy/no-identity-yet
    
    if incoming_pubkey:
        if not stored_pubkey:
            # TOFU: Pin the key
            print(f"[identity] TOFU: Pinning new key for {host_id}")
            storage.upsert_host(host_id, {
                "public_key": incoming_pubkey,
                "key_first_seen_utc": now_utc_str
            })
            # Re-fetch to ensure host_record has the key for subsequent logic
            host_record = storage.get_host(host_id)
            stored_pubkey = incoming_pubkey
        
        if incoming_sig:
            # First try the pinned key
            if verify_signature(payload, stored_pubkey, incoming_sig):
                if incoming_pubkey and incoming_pubkey != stored_pubkey:
                    identity_status = "KEY_MISMATCH"
                else:
                    identity_status = "VALID"
            else:
                # If pinned key fails, check if signature is valid for incoming key anyway
                if incoming_pubkey and verify_signature(payload, incoming_pubkey, incoming_sig):
                    identity_status = "KEY_MISMATCH"
                else:
                    identity_status = "INVALID_SIGNATURE"
        else:
            identity_status = "MISSING_SIGNATURE"
    elif stored_pubkey:
        identity_status = "MISSING_IDENTITY"

    # Soft-Mode Enforcement
    if identity_status != "VALID":
        _alert_log(f"IDENTITY_{identity_status}", {"host_id": host_id, "incoming_key": incoming_pubkey})
        health_hint = "YELLOW"
        # In Soft-Mode, we update health but do NOT block the heartbeat execution.

    # 2. Evaluate Attestation (Track A2)
    att_status, events, att_health = evaluate_attestation(host_record, incoming_att, now_utc_str)
    if att_health == "YELLOW": health_hint = "YELLOW"
    
    # 2b. Policy Engine Decision (Track A3 - Phase 2 Persistent)
    # Track A4: Map Identity Status to Policy
    effective_att_status = att_status
    if identity_status == "KEY_MISMATCH":
        effective_att_status = "SPOOF_SUSPECT"
    elif identity_status in ("INVALID_SIGNATURE", "MISSING_SIGNATURE", "MISSING_IDENTITY") and identity_status != "VALID":
        # Missing/Invalid results in at least DRIFT/WARN
        if effective_att_status == "OK":
            effective_att_status = "DRIFT"

    decision = policy_engine.decide(host_record, effective_att_status)
    
    # 3. Log Audit Events & Metrics
    for ev in events:
        details = ev["data"]
        details["host_id"] = host_id
        _audit_log(ev["event"], details)
        
    # Policy Enforcement & Alerts (A3 Phase 2)
    policy_updates = {}
    if "ALERT" in decision.actions:
        event_name = f"POLICY_{decision.state}"
        _alert_log(event_name, {"host_id": host_id, "reason": decision.reason, "attestation": att_status})
        
        # Persistent state update
        policy_updates = {
            "policy_state": decision.state,
            "policy_reason": decision.reason,
            "policy_until_utc": decision.until_utc,
            "policy_updated_utc": now_utc_str,
            "policy_hits": (host_record.get("policy_hits") or 0) + (1 if decision.state != "NORMAL" else 0)
        }

        # Standardized Telemetry
        metric_name = f"policy_{decision.state.lower()}_1m"
        record_module_call(source="policy", target=metric_name, duration_ms=0)

    # Record metrics via module call (simplified for v2.5.1)
    record_module_call(source="host_heartbeat", target=f"attestation_{att_status.lower()}", duration_ms=0)
    
    # 4. Final Upsert (Persists both Heartbeat, Attestation and Policy results)
    upsert_data = {
        "status": status,
        "health": health_hint or host_record.get("health", "GREEN"),
        "last_seen": now_utc_str,
        "attestation": host_record.get("attestation")
    }
    upsert_data.update(policy_updates)
    
    storage.upsert_host(host_id, upsert_data)
    
    print(f"[heartbeat] {host_id} -> status={status}, health={host_record.get('health')}, attestation={att_status}")
    
    # Legacy: Update discovery file (backward compatibility)
    try:
        hosts_file = storage.DATA_DIR.parent / "mesh" / "offgrid" / "discovery" / "mesh_hosts.json"
        if hosts_file.exists():
            data = json.loads(hosts_file.read_text(encoding="utf-8"))
            for url in data:
                if data[url].get("node_id") == host_id or host_id in url:
                    data[url]["active"] = (status == "online")
                    data[url]["last_seen"] = now_utc_str
                    data[url]["health"] = host_record.get("health", "GREEN")
            hosts_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[heartbeat] Failed to update legacy host status: {e}")
        
    return {"ok": True, "attestation_status": att_status}


# ------------------------------------------------------------------------------
# PROJECTS & FILES – EXPLORER
# ------------------------------------------------------------------------------

SHERATAN_ROOT = storage.config.BASE_DIR

@app.get("/api/projects")
def list_projects():
    """Lists subdirectories in the Sheratan root as projects."""
    projects = []
    try:
        # from datetime import datetime (already imported at top)
        for entry in os.scandir(SHERATAN_ROOT):
            if entry.is_dir() and not entry.name.startswith(('.', '_', 'Z_')):
                stats = entry.stat()
                projects.append({
                    "id": entry.name,
                    "name": entry.name.replace('_', ' ').title(),
                    "path": str(entry.path),
                    "status": "active",
                    "lastAccess": datetime.fromtimestamp(stats.st_atime).isoformat() + "Z",
                    "fileCount": 0
                })
    except Exception as e:
        print(f"[api] Error listing projects: {e}")
    return projects

@app.get("/api/projects/{project_id}/files", response_model=List[dict])
def list_project_files(project_id: str):
    """Returns a simple file tree for a project."""
    project_path = SHERATAN_ROOT / project_id
    if not project_path.exists() or not project_path.is_dir():
        raise HTTPException(404, "Project not found")
    
    def get_tree(path: Path, depth=0):
        if depth > 2: # Limit depth
            return []
        nodes = []
        try:
            for entry in os.scandir(path):
                if entry.name.startswith(('.', 'node_modules', '__pycache__', '.git')):
                    continue
                node = {
                    "name": entry.name,
                    "path": str(entry.path),
                    "type": "directory" if entry.is_dir() else "file"
                }
                if entry.is_dir():
                    node["children"] = get_tree(Path(entry.path), depth + 1)
                nodes.append(node)
        except Exception:
            pass
        return nodes

    return get_tree(project_path)



@app.post("/metrics/module-calls")
def post_module_metrics(payload: dict):
    """Telemetry endpoint for internal module calls (fire-and-forget)."""
    # For now just log to terminal if needed, or just return 200
    # print(f"[metrics] {payload.get('source')} -> {payload.get('target')} ({payload.get('duration_ms')}ms)")
    return {"ok": True}

@app.get("/api/system/baselines")
def get_performance_baselines():
    """Returns performance baselines for all tracked metrics (Step 1)."""
    return baseline_tracker.get_all_baselines(recompute=True)

@app.get("/api/system/diagnostic")
def get_system_diagnostic():
    """Returns latest health report from Self-Diagnostic Engine (Step 3)."""
    return diagnostic_engine.get_latest_report()

@app.post("/api/system/diagnostic/trigger")
def trigger_diagnostic(diagnostic_type: str = "manual"):
    """Manually trigger a diagnostic check (Step 3)."""
    return diagnostic_engine.run_diagnostic(diagnostic_type)

@app.get("/api/system/anomalies")
def get_detected_anomalies(window: str = "1h", limit: int = 100):
    """Returns detected anomalies from Anomaly Detector (Step 2)."""
    return anomaly_detector.get_anomalies(window=window, limit=limit)

import asyncio

# --- OBSOLETE BLOCK REMOVED ---


# ------------------------------------------------------------------------------
# MISC – HEALTH ENDPOINT
# ------------------------------------------------------------------------------

@app.get("/api/status")
def status():
    """Consolidated status endpoint for quick checks."""
    metrics = health_manager.get_system_metrics()
    return {
        "status": "operational",
        "uptime_sec": metrics["uptime_sec"],
        "memory": metrics["memory"],
        "cpu_percent": metrics["cpu_pct"],
        "storage": metrics["storage"],
        "config": {
            "max_queue": RobustnessConfig.MAX_QUEUE_DEPTH,
            "max_inflight": RobustnessConfig.MAX_INFLIGHT,
            "backpressure_mode": RobustnessConfig.BACKPRESSURE_MODE
        }
    }


# ------------------------------------------------------------------------------
# PHASE A: STATE MACHINE ENDPOINTS
# ------------------------------------------------------------------------------

# Internal helper removed in favor of health_manager.evaluate_full_health()


@app.get("/api/system/state")
async def get_system_state():
    """Get current system state with reasoning."""
    snap = state_machine.snapshot()
    health = await health_manager.evaluate_full_health()
    
    # Calculate uptime in current state
    state_duration = time.time() - snap.since_ts
    
    return {
        "state": snap.state,
        "since": snap.since_ts,
        "duration_sec": int(state_duration),
        "health": health,
        "counters": snap.counters or {},
        "last_transition": snap.last_transition
    }


@app.post("/api/system/state/transition")
async def transition_system_state(payload: dict):
    """Manually trigger a state transition."""
    next_state_str = payload.get("state")
    reason = payload.get("reason")
    actor = payload.get("actor", "user")
    
    if not next_state_str or not reason:
        raise HTTPException(400, "Missing 'state' or 'reason'")
    
    try:
        next_state = SystemState(next_state_str)
    except ValueError:
        raise HTTPException(400, f"Invalid state: {next_state_str}")
    
    try:
        event = state_machine.transition(
            next_state,
            reason=reason,
            actor=actor,
            meta=payload.get("meta")
        )
        return {
            "ok": True,
            "event": {
                "event_id": event.event_id,
                "from": event.prev_state,
                "to": event.next_state,
                "reason": event.reason,
                "timestamp": event.ts
            }
        }
    except Exception as e:
        raise HTTPException(400, str(e))


@app.get("/api/system/state/history")
def get_state_history(limit: int = 50):
    """Get recent state transitions from log."""
    import os
    log_path = state_machine.log_path
    
    if not os.path.exists(log_path):
        return []
    
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # Get last N lines
        recent = lines[-limit:] if len(lines) > limit else lines
        
        events = []
        for line in recent:
            try:
                event = json.loads(line.strip())
                events.append(event)
            except:
                pass
        
        return events
    except Exception as e:
        raise HTTPException(500, f"Error reading state history: {e}")


# ------------------------------------------------------------------------------
# GATEWAY ENDPOINTS
# ------------------------------------------------------------------------------

@app.get("/api/gateway/config")
def get_gateway_config(request: Request):
    """
    Get gateway configuration and statistics.
    Restricted to Localhost (127.0.0.1) for security.
    """
    # 1. Localhost lockdown
    client_host = request.client.host if request.client else "unknown"
    is_local = client_host in ("127.0.0.1", "::1", "localhost")
    
    # 2. Token-Auth (optional but recommended for internal services)
    token = request.headers.get("X-Sheratan-Token") or request.headers.get("Authorization", "").replace("Bearer ", "")
    expected = os.getenv("SHERATAN_HUB_TOKEN", "shared-secret")
    has_valid_token = token == expected

    if not (is_local or has_valid_token):
        print(f"[gateway] UNAUTHORIZED config access attempt from {client_host}")
        raise HTTPException(status_code=403, detail="Forbidden: Internal config access restricted.")

    from core.gateway_middleware import get_gateway_stats
    return get_gateway_stats()


# ------------------------------------------------------------------------------
# ROOT
# ------------------------------------------------------------------------------

@app.get("/")
def root():
    return JSONResponse({"sheratan_core_v2": "running", "version": "0.3.0"})


# ------------------------------------------------------------------------------
# SYSTEM OBSERVABILITY & HEALTH (Track C1-C3)
# ------------------------------------------------------------------------------

@app.get("/api/system/health")
async def get_system_health():
    """Legacy endpoint for HealthTab (List of services)."""
    health = await health_manager.evaluate_full_health()
    return health["service_list"]

@app.get("/api/system/health/ops")
async def get_ops_health():
    """Detailed health status for OpsTab."""
    health = await health_manager.evaluate_full_health()
    metrics = health_manager.get_system_metrics()
    
    return {
        "status": health["overall"].upper(),
        "version": "v0.3.0",
        "uptime_sec": metrics["uptime_sec"],
        "db": "OK" if health["db_ok"] else "ERROR",
        "queue": {
            "depth": metrics["storage"]["queue_depth"],
            "inflight": metrics["storage"]["inflight"],
            "max": RobustnessConfig.MAX_QUEUE_DEPTH,
            "max_inflight": RobustnessConfig.MAX_INFLIGHT
        },
        "violations": slo_manager.active_violations,
        "services": health["services"]
    }

# System observability endpoints unified below.
@app.get("/api/system/metrics")
async def get_system_metrics():
    """Hybrid metrics snapshot (Supports Legacy HealthTab and Modern OpsTab)."""
    health = await health_manager.evaluate_full_health()
    metrics = health_manager.get_system_metrics()
    
    from core.gateway_middleware import get_gateway_stats
    gw = get_gateway_stats()
    
    # Calculate error rate (internal legacy measure)
    failed = storage.count_recent_errors(limit=100)
    error_rate = round((failed / 100 * 100), 2)
    
    return {
        # --- LEGACY FLAT KEYS (HealthTab) ---
        "cpu": metrics["cpu_pct"],
        "memory": metrics["memory"]["percent"],
        "queueLength": metrics["storage"]["queue_depth"],
        "errorRate": error_rate,
        "uptime": metrics["uptime_sec"],
        
        # --- MODERN NESTED OBJECTS (OpsTab) ---
        "status": health["overall"],
        "uptime_sec": metrics["uptime_sec"],
        "process": {
            "cpu_pct": metrics["process"]["cpu_pct"],
            "mem_mb": metrics["process"]["memory_rss"] / (1024 * 1024),
            "memory_pct": metrics["memory"]["percent"]
        },
        "queue": {
            "depth": metrics["storage"]["queue_depth"],
            "inflight": metrics["storage"]["inflight"],
            "max": RobustnessConfig.MAX_QUEUE_DEPTH,
            "max_inflight": RobustnessConfig.MAX_INFLIGHT
        },
        "idempotency": {
            "hits": IDEMPOTENT_HITS_COUNTER,
            "collisions": IDEMPOTENCY_COLLISIONS_COUNTER
        },
        "integrity": {
            "failures": INTEGRITY_FAILURES_COUNTER,
            "hash_writes": HASH_WRITES_COUNTER,
            "migrations": HASH_MIGRATIONS_COUNTER
        },
        "gateway": gw.get("stats", {}),
        "config": {
            "backpressure_mode": RobustnessConfig.BACKPRESSURE_MODE
        }
    }

@app.get("/api/system/alerts")
async def get_system_alerts(limit: int = 100):
    """Fetch recent alerts from the log file (Optimized tail-read)."""
    alert_file = storage.DATA_DIR / "logs" / "alerts.jsonl"
    if not alert_file.exists():
        return []
    
    alerts = []
    try:
        with alert_file.open("rb") as f:
            try:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                offset = max(0, size - 65536) # Read last 64kb
                f.seek(offset)
                chunk = f.read().decode("utf-8", errors="ignore")
                lines = chunk.splitlines()
                # Get the last 'limit' lines, excluding potentially partial first line
                start_idx = 0 if offset == 0 else 1
                for line in reversed(lines[start_idx:]):
                    if not line.strip(): continue
                    try:
                        alerts.append(json.loads(line))
                        if len(alerts) >= limit: break
                    except:
                        continue
            except Exception:
                f.seek(0)
                lines = f.readlines()
                for line in reversed(lines[-limit:]):
                    try:
                        alerts.append(json.loads(line))
                    except:
                        continue
    except Exception as e:
        print(f"[api] Error reading alerts: {e}")
        return []
    
    return alerts

@app.post("/api/system/diagnostics/trigger")
async def trigger_diagnostics():
    """Trigger a new diagnostic bundle creation."""
    try:
        import subprocess
        script_path = BASE_DIR / "scripts" / "diagnose.ps1"
        if not script_path.exists():
            return {"status": "error", "message": "Diagnostic script not found"}
            
        # Run as detached process (Track C3)
        subprocess.Popen(["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", str(script_path),
                         "-CustomRepoRoot", str(BASE_DIR),
                         "-CustomDataDir", str(storage.DATA_DIR)],
                         cwd=str(BASE_DIR), 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL)
        return {"status": "triggered", "message": "Generation started"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/system/diagnostics/list")
async def list_diagnostics():
    """List available diagnostic bundles."""
    diag_dir = storage.DATA_DIR / "diagnostics"
    if not diag_dir.exists():
        return []
        
    bundles = []
    try:
        for f in diag_dir.glob("sheratan_diag_*.zip"):
            stats = f.stat()
            bundles.append({
                "name": f.name,
                "ts": datetime.fromtimestamp(stats.st_mtime).isoformat() + "Z",
                "size_mb": round(stats.st_size / (1024 * 1024), 2)
            })
    except Exception:
        pass
    return sorted(bundles, key=lambda x: x["ts"], reverse=True)


# ------------------------------------------------------------------------------
# QUICK START – MISSION TEMPLATES
# ------------------------------------------------------------------------------

@app.post("/api/missions/standard-code-analysis")
def create_standard_code_analysis():
    """Boss Directive 4.1: One-click playground mission directly in Core."""
    title = "System verstehen"
    description = (
        "Analysiere die Scripts des aktuellen Systems, erstelle ein Lagebild "
        "und mache dir Notizen in der Mission-Plan Datei."
    )

    # 1. Create Mission (using model)
    mission_create = models.MissionCreate(
        title=title,
        description=description,
        metadata={"created_by": "dashboard_quickstart", "max_iterations": 100}
    )
    mission = models.Mission.from_create(mission_create)
    storage.create_mission(mission)

    # 2. Create agent_plan Task
    task_create = models.TaskCreate(
        name="Initial codebase analysis",
        description="Let the agent inspect the codebase and plan followup jobs.",
        kind="agent_plan",
        params={
            "user_prompt": f"Analysiere das Repository unter {SHERATAN_ROOT} und erstelle ein Lagebild. Beachte: Die Core-Logik liegt in core/.",
            "project_root": str(SHERATAN_ROOT)
        }
    )
    task = models.Task.from_create(mission.id, task_create)
    storage.create_task(task)

    # 3. Create Job (properly structured for worker)
    job_create = models.JobCreate(
        payload={
            "task": {
                "kind": "agent_plan",
                "params": task_create.params
            },
            "params": {
                **task_create.params,
                "iteration": 1
            }
        }
    )
    job = models.Job.from_create(task.id, job_create)
    storage.create_job(job)

    # 4. Auto-Queue (Dispatcher takes over)
    print(f"[api] QuickStart mission created: {mission.id[:8]}. Job {job.id[:8]} queued.")
    
    return {
        "mission": {"id": mission.id, "title": mission.title},
        "task": {"id": task.id, "name": task.name},
        "job": {"id": job.id}
    }

@app.post("/api/missions/agent-plan")
def create_agent_plan_mission(payload: dict):
    """Generic entry point for natural language missions."""
    prompt = payload.get("user_prompt")
    if not prompt:
        raise HTTPException(400, "Missing user_prompt")
        
    title = f"Mission: {prompt[:30]}..."
    description = prompt
    
    # 1. Create Mission
    mission_create = models.MissionCreate(
        title=title,
        description=description,
        metadata={"created_by": "mission_control", "type": "autonomous", "max_iterations": 100}
    )
    mission = models.Mission.from_create(mission_create)
    storage.create_mission(mission)
    
    # 2. Create agent_plan Task
    task_create = models.TaskCreate(
        name="Autonomous Planning",
        description="Plan and execute based on user prompt.",
        kind="agent_plan",
        params={
            "user_prompt": prompt,
            "project_root": str(SHERATAN_ROOT)
        }
    )
    task = models.Task.from_create(mission.id, task_create)
    storage.create_task(task)
    
    # 3. Create Job
    job_create = models.JobCreate(
        payload={
            "task": {
                "kind": "agent_plan",
                "params": task_create.params
            },
            "params": {
                **task_create.params,
                "iteration": 1
            }
        }
    )
    job = models.Job.from_create(task.id, job_create)
    storage.create_job(job)
    
    return {
        "mission": {"id": mission.id, "title": mission.title},
        "task": {"id": task.id, "name": task.name},
        "job": {"id": job.id}
    }


# ------------------------------------------------------------------------------
# MESH WORKER REGISTRATION
# ------------------------------------------------------------------------------

@app.post("/api/mesh/workers/register")
def register_worker(worker_data: dict):
    """Register a worker in the Mesh Registry."""
    try:
        from mesh.registry.mesh_registry import WorkerRegistry, WorkerInfo, WorkerCapability
        from pathlib import Path
        
        registry_file = Path(__file__).parent.parent / "mesh" / "registry" / "workers.json"
        registry = WorkerRegistry(registry_file)
        
        # Convert capabilities dict to WorkerCapability objects
        capabilities = [
            WorkerCapability(kind=cap['kind'], cost=cap['cost'])
            for cap in worker_data.get('capabilities', [])
        ]
        
        worker_info = WorkerInfo(
            worker_id=worker_data['worker_id'],
            capabilities=capabilities,
            status=worker_data.get('status', 'online'),
            endpoint=worker_data.get('endpoint'),
            meta=worker_data.get('meta', {})
        )
        
        registry.register(worker_info)
        
        print(f"[mesh] ✓ Registered worker: {worker_data['worker_id']} with {len(capabilities)} capabilities")
        
        return {
            "ok": True,
            "worker_id": worker_data['worker_id'],
            "message": f"Worker registered successfully"
        }
    except Exception as e:
        print(f"[mesh] ✗ Registration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/mesh/workers")
def list_workers():
    """List all registered workers."""
    try:
        from mesh.registry.mesh_registry import WorkerRegistry
        from pathlib import Path
        
        registry_file = Path(__file__).parent.parent / "mesh" / "registry" / "workers.json"
        registry = WorkerRegistry(registry_file)
        registry.load()
        
        workers = []
        for worker_id, worker_info in registry.workers.items():
            workers.append({
                "worker_id": worker_id,
                "capabilities": [{"kind": c.kind, "cost": c.cost} for c in worker_info.capabilities],
                "status": worker_info.status,
                "last_seen": worker_info.last_seen,
                "stats": {
                    "n": worker_info.stats.n,
                    "success_ema": worker_info.stats.success_ema,
                    "latency_ms_ema": worker_info.stats.latency_ms_ema,
                    "consecutive_failures": worker_info.stats.consecutive_failures,
                    "is_offline": worker_info.stats.is_offline,
                    "cooldown_until": worker_info.stats.cooldown_until,
                    "active_jobs": worker_info.stats.active_jobs
                },
                "meta": worker_info.meta
            })
        
        return workers
    except Exception as e:
        print(f"[mesh] Error listing workers: {e}")
        return []


@app.get("/api/admin/policies")
def list_active_policies(request: Request):
    """Admin only: List hosts with active policies."""
    # Localhost security check
    if request.client.host not in ("127.0.0.1", "localhost"):
         raise HTTPException(status_code=403, detail="Forbidden: Admin access restricted to localhost")
    
    return storage.list_policies()

@app.post("/api/admin/policies/clear")
def clear_host_policy(request: Request, payload: dict):
    """Admin only: Manually clear a host's policy."""
    if request.client.host not in ("127.0.0.1", "localhost"):
         raise HTTPException(status_code=403, detail="Forbidden: Admin access restricted to localhost")
    
    host_id = payload.get("host_id")
    if not host_id:
        return {"ok": False, "error": "missing_host_id"}
    
    storage.clear_policy(host_id, by="admin_manual")
    _audit_log("POLICY_CLEARED_MANUAL", {"host_id": host_id, "by": "admin"})
    
    return {"ok": True, "message": f"Policy cleared for {host_id}"}


if __name__ == "__main__":
    import uvicorn
    import multiprocessing
    multiprocessing.freeze_support()
    # Start on 8001 as specified in DASHBOARDS.md
    print("--- Sheratan Core v2 starting on http://localhost:8001 ---")
    
    # Auto-launch dashboard if frozen (Track D4)
    if getattr(sys, 'frozen', False):
        def _launch():
            time.sleep(2.0)
            webbrowser.open("http://localhost:8001/ui/")
        threading.Thread(target=_launch, daemon=True).start()
        print("[core] Bundle detected: Dashboard auto-launch scheduled")

    uvicorn.run(app, host="0.0.0.0", port=8001)
