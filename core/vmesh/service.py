# core/vmesh/service.py
from __future__ import annotations
import asyncio
import time
from typing import Optional, Dict, Any
from core.vmesh.stability import StabilityEvaluator, VMeshState
from core.vmesh.complexity import ComplexityTracker
from core.vmesh.sync import SynchronizationLayer
from core.vmesh.controller import VMeshController, PolicyMode
from core.vmesh.runtime import vmesh_runtime
from core import storage

class VMeshService:
    """
    VMesh Service Orchestrator.
    Gathers metrics, evaluates stability, and enforces the policy mode.
    """
    def __init__(
        self,
        evaluator: StabilityEvaluator,
        complexity: ComplexityTracker,
        sync: SynchronizationLayer,
        check_interval_sec: int = 5
    ):
        self.controller = VMeshController(evaluator, complexity, sync)
        self.check_interval_sec = check_interval_sec
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self.metric_sources: Dict[str, Any] = {}

    def register_source(self, name: str, source: Any):
        """Register a source (callable or object) to be polled for metrics."""
        self.metric_sources[name] = source

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        print(f"[vmesh] Service started (interval={self.check_interval_sec}s)")

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    async def _run_loop(self):
        while self._running:
            try:
                state = await self._gather_metrics()
                mode = self.controller.decide_mode(state)
                
                # Update global runtime state for enforcement
                vmesh_runtime.current_mode = mode
                vmesh_runtime.last_update_ts = time.time()
                vmesh_runtime.stability_s = self.controller.evaluator._last_score
                vmesh_runtime.sync_score = self.controller.sync.get_global_sync()
                
                if mode != PolicyMode.NORMAL:
                    # Optional: Log non-normal transitions or status
                    # In a real integration, we'd use _alert_log from main.py
                    pass

            except Exception as e:
                print(f"[vmesh] Loop error: {e}")
            
            await asyncio.sleep(self.check_interval_sec)

    async def _gather_metrics(self) -> VMeshState:
        """
        Gathers real-time metrics from the Sheratan Core.
        """
        # 1. Queue Age (Max pending time)
        pending_jobs = storage.list_jobs()
        pending = [j for j in pending_jobs if j.status == "pending"]
        max_age = 0.0
        if pending:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            ages = []
            for j in pending:
                try:
                    created_at = datetime.fromisoformat(j.created_at.replace("Z", "+00:00"))
                    ages.append((now - created_at).total_seconds())
                except:
                    continue
            if ages:
                max_age = max(ages)

        # 2. Error Rate (Recent jobs)
        recent_jobs = pending_jobs[-100:] if pending_jobs else []
        failed = [j for j in recent_jobs if j.status == "failed"]
        error_rate = len(failed) / len(recent_jobs) if recent_jobs else 0.0

        # 3. Latency (Try to get from source, else default)
        latency_p95 = 200.0
        if "latency" in self.metric_sources:
            try:
                lat_source = self.metric_sources["latency"]
                latency_p95 = lat_source() if callable(lat_source) else lat_source
            except: pass

        # 4. Ledger Conflicts
        ledger_conflicts = 0
        if "ledger_conflicts" in self.metric_sources:
            try:
                conf_source = self.metric_sources["ledger_conflicts"]
                ledger_conflicts = conf_source() if callable(conf_source) else conf_source
            except: pass
        
        return VMeshState(
            latency_p95_ms=latency_p95,
            error_rate=error_rate,
            queue_age_p95_sec=max_age,
            ledger_conflicts=int(ledger_conflicts),
            fallback_cascade_depth=0, # TODO: Wire fallback tracking
            timestamp=time.time()
        )
