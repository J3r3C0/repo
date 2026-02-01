from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Request
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
import sys
import os
from pathlib import Path

from core.config import BASE_DIR
from core.engine import SheratanEngine

# Add parent directory to sys.path so 'core' module can be imported
if str(Path(BASE_DIR)) not in sys.path:
    sys.path.insert(0, str(Path(BASE_DIR)))

<<<<<<< HEAD
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
from core.config import RobustnessConfig
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
=======
ENABLE_RESET = os.getenv("SHERATAN_ENABLE_RESET", "0") == "1"
>>>>>>> 0d05299baf01209327a7b0a1e6eb7b526f866bcb

# --- Engineering Logic ---
class EngineConfig:
    WINDOW_SIZE = 1000
    DEFAULT_WEIGHT = 1.0
    DEFAULT_DECAY = 0.95
    max_active_states = 1000
    MAX_SEGMENT_AGE = 1000

<<<<<<< HEAD
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
=======
engine = SheratanEngine(EngineConfig)
>>>>>>> 0d05299baf01209327a7b0a1e6eb7b526f866bcb

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[core] Perception Kernel Operational")
    yield
    print("[core] perception Kernel Shutdown")

# --- App Initialize ---
app = FastAPI(
    title="Sheratan Core",
    description="Deterministic Perception Kernel",
    version="0.5.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

<<<<<<< HEAD
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

=======
>>>>>>> 0d05299baf01209327a7b0a1e6eb7b526f866bcb
# ------------------------------------------------------------------------------
# CORE OBSERVER API (PERCEPTION-ONLY)
# ------------------------------------------------------------------------------

@app.post("/api/event")
async def post_event(payload: dict):
    """
    Ingests a batch of raw events into the resonance core.
    Format: {"events": [(id, value, ts, ch), ...]}
    """
    events = payload.get("events", [])
    if not events:
        return {"ok": False, "error": "empty_events"}
    
    try:
        resonances = engine.process_events(events)
        return {"ok": True, "resonances": resonances}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/state")
async def get_state():
    """
    Returns a snapshot of the current resonance memory states.
    Includes the deterministic state_hash.
    """
    try:
        states = engine.get_state_snapshot()
        state_hash = engine.memory.get_state_hash()
        results = []
        for s in states:
            results.append({
                "segment": int(s["segment"]),
                "value": float(s["value"]),
                "weight": float(s["weight"]),
                "decay": float(s["decay"]),
                "last_seen": int(s["last_seen"])
            })
        return {"ok": True, "state_hash": state_hash, "states": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/identity")
async def get_identity(threshold: float = 0.5, top_k: int = 10):
    """
    Returns the selected top resonance states (Identity Layer).
    Includes persistence and age-based ranking + state_hash.
    """
    try:
        from core.identity import select_top_states
        states = engine.get_state_snapshot()
        state_hash = engine.memory.get_state_hash()
        
        # Gate B: Use persistence and engine state
        selected = select_top_states(
            states, 
            threshold=threshold, 
            top_k=top_k,
            current_cycle=engine.cycle_count,
            last_selected_segments=getattr(engine, "_last_selected", set())
        )
        
        # Save for next turn's persistence check
        engine._last_selected = {int(s["segment"]) for s in selected}
        
        results = []
        for s in selected:
            results.append({
                "segment": int(s["segment"]),
                "value": float(s["value"]),
                "weight": float(s["weight"]),
                "decay": float(s["decay"]),
                "last_seen": int(s["last_seen"])
            })
        return {"ok": True, "state_hash": state_hash, "selected_states": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/replay")
async def post_replay(payload: dict):
    """
    Triggers deterministic state reconstruction from a resonance log file.
    Format: {"log_path": "path/to/resonance_log.csv"}
    """
    log_path = payload.get("log_path")
    if not log_path or not os.path.exists(log_path):
        raise HTTPException(status_code=400, detail="log_path_missing_or_invalid")
    
    try:
        count = engine.replay_from_log(log_path)
        state_hash = engine.memory.get_state_hash()
        return {"ok": True, "reconstructed_segments": count, "state_hash": state_hash}
    except Exception as e:
<<<<<<< HEAD
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
=======
>>>>>>> 0d05299baf01209327a7b0a1e6eb7b526f866bcb
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reset")
async def post_reset():
    """
    Resets the perception kernel to its initial deterministic state.
    Gated by SHERATAN_ENABLE_RESET environment variable.
    """
    if not ENABLE_RESET:
        raise HTTPException(status_code=403, detail="Reset disabled. Set SHERATAN_ENABLE_RESET=1")
    
    try:
        engine.reset()
        state_hash = engine.memory.get_state_hash()
        return {
            "ok": True, 
            "cycle_count": engine.cycle_count, 
            "state_hash": state_hash,
            "segment_count": len(engine.memory.states)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/identity/{segment_id}")
async def get_segment_state(segment_id: int):
    """
    Returns the detailed resonance memory state for a specific segment.
    """
    try:
        if segment_id in engine.memory.states:
            s = engine.memory.states[segment_id]
            return {
                "ok": True, 
                "segment": segment_id,
                "value": float(s["value"]),
                "weight": float(s["weight"]),
                "decay": float(s["decay"]),
                "last_seen": int(s["last_seen"])
            }
        else:
            raise HTTPException(status_code=404, detail="segment_not_found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def root():
    return {"sheratan_core": "perception_v2", "status": "operational"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)

