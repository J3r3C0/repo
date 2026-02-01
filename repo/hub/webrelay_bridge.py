# sheratan_core_v2/webrelay_bridge.py
import json
import uuid
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from core import config
from hub import storage, models
from hub.envelope import build_job_envelope_v1

# Import mesh ledger and registry from local mesh/registry module
try:
    from mesh.registry.client import LedgerClient, PaymentRequiredError
    from mesh.registry.mesh_registry import WorkerRegistry, WorkerInfo, WorkerCapability
except ImportError:
    # Fallback if mesh.registry not in path
    LedgerClient = None
    WorkerRegistry = None
    PaymentRequiredError = None


class WebRelaySettings:
    def __init__(self, relay_out_dir: Path, relay_in_dir: Path, session_prefix: str = "core_v2"):
        self.relay_out_dir = Path(relay_out_dir)
        self.relay_in_dir = Path(relay_in_dir)
        self.session_prefix = session_prefix


class WebRelayBridge:
    """
    Handles writing unified job files for the worker and reading back results.
    """

    def __init__(self, settings: Optional[WebRelaySettings] = None):
        self.settings = settings
        
        # Standard webrelay paths (relative to BASE_DIR)
        self.relay_out_dir = config.DATA_DIR / "webrelay_out"
        self.relay_in_dir = config.DATA_DIR / "webrelay_in"
        
        self.relay_out_dir.mkdir(parents=True, exist_ok=True)
        self.relay_in_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Mesh components
        self.ledger = None
        self.registry = None
        
        if LedgerClient:
            ledger_url = os.getenv("SHERATAN_LEDGER_URL")
            # Use local ledger.json in mesh/registry/
            ledger_path = config.BASE_DIR / "mesh" / "registry" / "ledger.json"

            if ledger_url:
                self.ledger = LedgerClient(base_url=ledger_url)
            elif ledger_path.exists():
                self.ledger = LedgerClient(json_path=str(ledger_path))
                
        if WorkerRegistry:
            # Use local workers.json in mesh/registry/
            registry_path = config.BASE_DIR / "mesh" / "registry" / "workers.json"
            
            if registry_path.exists():
                self.registry = WorkerRegistry(registry_path)

    # --------------------------------------------------------------
    # KIND MAPPING FOR WORKER
    # --------------------------------------------------------------
    def _infer_job_kind(self, task: models.Task) -> str:
        """Infer job kind from task metadata."""
        # Check task.kind first (explicit)
        if task.kind and task.kind.strip():
            return task.kind
        
        # Fallback: infer from task name
        name = task.name.lower()

        # Discovery → list_files
        if "discovery" in name or "list_files" in name:
            return "list_files"

        # Analyzer
        if "analyze" in name:
            return "analyze_file"

        # Writer
        if "write" in name:
            return "write_file"

        # Patcher
        if "update" in name or "patch" in name:
            return "patch_file"

        return "llm_call"


    # --------------------------------------------------------------
    # WRITE UNIFIED JOB FILE
    # --------------------------------------------------------------
    def enqueue_job(self, job_id: str) -> Path:
        job = storage.get_job(job_id)
        if job is None:
            raise ValueError("Job not found")

        task = storage.get_task(job.task_id)
        if task is None:
            raise ValueError("Task not found")

        mission = storage.get_mission(task.mission_id)
        if mission is None:
            raise ValueError("Mission not found")

        # Phase 10: Prioritize explicit kind in job payload (child jobs)
        kind = job.payload.get("kind")
        if not kind:
            kind = self._infer_job_kind(task)

        # ----------------------------------------------------------
        # Job schema unification (v1.1.1)
        # We emit a canonical JobEnvelope v1.
        # ----------------------------------------------------------
        params = job.payload.get("params", {})
        if not isinstance(params, dict):
            params = {}
        
        payload_dict = job.payload if isinstance(job.payload, dict) else {}
        
        # Merge core fields
        for key in ["context", "last_result", "history"]:
            if key in payload_dict and key not in params:
                params[key] = payload_dict[key]
        
        # Legacy prompt mapping
        if not params.get("prompt"):
             if "prompt" in payload_dict:
                 params["prompt"] = payload_dict["prompt"]
             elif "user_prompt" in payload_dict:
                 params["prompt"] = payload_dict["user_prompt"]

        envelope = build_job_envelope_v1(
            job_id=job.id,
            kind=kind,
            params=params,
            mission_id=mission.id,
            task_id=task.id,
            chain_id=task.params.get("chain_id"),
            trace_id=(job.payload.get("mcts_trace", {}) or {}).get("trace_id"),
            source_zone=(mission.metadata or {}).get("source_zone", "internal"),
            build_id=os.getenv("SHERATAN_BUILD_ID", "main-v2"),
            node_id=os.getenv("SHERATAN_NODE_ID"),
            identity=os.getenv("SHERATAN_NODE_IDENTITY"),
        )

        # Attach legacy payload expected by existing WebRelay workers.
        envelope.update(
            {
                "kind": kind,
                "session_id": f"{self.settings.session_prefix if self.settings else 'core_v2'}_{mission.id}",
                "created_at": job.created_at,
                "payload": {
                    "response_format": "lcp",
                    "mission": mission.to_dict(),
                    "task": task.to_dict(),
                    "params": params,
                    "context": params.get("context"),
                    "last_result": job.payload.get("last_result"),
                },
            }
        )

        job_file = self.relay_out_dir / f"{job_id}.job.json"
        with open(job_file, "w", encoding="utf-8") as f:
            json.dump(envelope, f, indent=2)

        return job_file




        envelope = build_job_envelope_v1(
            job_id=job.id,
            kind=kind,
            params=params,
            mission_id=mission.id,
            task_id=task.id,
            chain_id=chain_id,
            trace_id=(job.payload.get("mcts_trace", {}) or {}).get("trace_id"),
            source_zone=(mission.metadata or {}).get("source_zone", "internal"),
            build_id=os.getenv("SHERATAN_BUILD_ID", "main-v2"),
            node_id=os.getenv("SHERATAN_NODE_ID"),
            identity=os.getenv("SHERATAN_NODE_IDENTITY"),
        )

        # Attach legacy payload expected by existing WebRelay workers.
        envelope.update(
            {
                "kind": kind,
                "worker_id": worker_id,  # Target worker
                "cost": cost,  # Paid tokens
                "session_id": f"{self.settings.session_prefix if self.settings else 'core_v2'}_{mission.id}",
                "created_at": job.created_at,
                "payload": {
                    "response_format": "lcp",
                    "mission": mission.to_dict(),
                    "task": task.to_dict(),
                    "params": params,
                    "context": params.get("context"), # Explicit context for WebRelay
                    "artifacts": artifacts,
                    "last_result": job.payload.get("last_result"),
                },
            }
        )


        unified = envelope
        job_file = self.relay_out_dir / f"{job_id}.job.json"

        # Phase Mesh: Direct HTTP Dispatch fallback
        # If the worker has an endpoint and isn't webrelay_worker, try to dispatch via POST.
        worker_info = self.registry.workers.get(worker_id) if self.registry else None
        has_http_endpoint = worker_info and worker_info.endpoint and worker_id not in ["webrelay_worker", "default_worker"]
        
        print(f"[debug-bridge] job={job.id[:8]} worker={worker_id} has_http={has_http_endpoint} reg_keys={list(self.registry.workers.keys()) if self.registry else 'None'}")
        
        if has_http_endpoint:
            try:
                import requests
                target_url = f"{worker_info.endpoint.rstrip('/')}/run"
                if "localhost" in target_url:
                    target_url = target_url.replace("localhost", "127.0.0.1")
                print(f"[bridge] 🚀 Direct HTTP Dispatch to {worker_id} ({target_url})")
                
                # Use a reasonable timeout
                resp = requests.post(target_url, json=unified, timeout=300)
                if resp.status_code == 200:
                    # Write result to relay_in so sync_step handles it normally
                    result_file = self.relay_in_dir / f"{job.id}.result.json"
                    
                    # Wrap in result_envelope_v1 if it isn't already
                    res_data = resp.json()
                    if res_data.get("schema_version") != "result_envelope_v1":
                        wrapped = {
                            "schema_version": "result_envelope_v1",
                            "job_id": job.id,
                            "ok": res_data.get("ok", True),
                            "result": {
                                "summary": f"HTTP result from {worker_id}",
                                "data": res_data
                            }
                        }
                        res_data = wrapped
                        
                    with open(result_file, "w", encoding="utf-8") as rf:
                        json.dump(res_data, rf, indent=2)
                    
                    print(f"[bridge] ✅ HTTP Dispatch Success for {job.id[:8]}")
                    return None # No job file needed for file watcher
                else:
                    print(f"[bridge] ⚠️ HTTP Dispatch failed (status={resp.status_code}). Falling back to file.")
            except Exception as http_err:
                print(f"[bridge] ⚠️ HTTP Dispatch error: {http_err}. Falling back to file.")

        unified = envelope
        print(f"[debug-bridge] Writing {job_file}...")
        print(f"[debug-bridge] unified keys: {list(unified.keys())}")
        if "payload" in unified:
            print(f"[debug-bridge] payload keys: {list(unified['payload'].keys())}")
            if "context" in unified["payload"]:
                print(f"[debug-bridge] ✅ CONTEXT IS IN PAYLOAD!")

        with open(job_file, "w", encoding="utf-8") as f:
            json.dump(unified, f, indent=2)


        return job_file

    # --------------------------------------------------------------
    # READ AND PROCESS RESULT FILES
    # --------------------------------------------------------------
    def try_sync_result(self, job_id: str, remove_after_read: bool = True) -> Optional[models.Job]:
        job = storage.get_job(job_id)
        if job is None:
            return None

        result_file = self.relay_in_dir / f"{job_id}.result.json"

        if not result_file.exists():
            return None

        try:
            raw = result_file.read_text()
            print(f"[bridge] 📨 Syncing result for job {job_id[:8]}... RAW length: {len(raw)}")
            content = json.loads(raw)
        except Exception:
            job.status = "failed"
            job.result = {"ok": False, "error": "invalid_json"}
            job.updated_at = datetime.utcnow().isoformat() + "Z"
            storage.update_job(job)
            if remove_after_read:
                result_file.unlink(missing_ok=True)
            return job

        # ------------------------------------------------------
        # Result schema unification (v1.1.1)
        # Support canonical ResultEnvelope v1, while staying back-compat
        # with legacy {ok:bool,...} results.
        # ------------------------------------------------------

        if isinstance(content, dict) and content.get("schema_version") == "result_envelope_v1":
            ok = bool(content.get("ok", True))
            status = content.get("status") or ("completed" if ok else "failed")

            # Inner data is what LCP/Phase 10 followup logic expects.
            inner = content.get("result", {})
            if isinstance(inner, dict):
                inner_data = inner.get("data")
            else:
                inner_data = None

            job.result = inner_data if isinstance(inner_data, dict) else content

            if status in ["completed", "ok", "success"] and ok:
                job.status = "completed"
            else:
                job.status = "failed"

            # Keep full envelope for audit/debug without breaking existing fields
            job.payload["last_result_envelope"] = content
        else:
            job.result = content
            if not content.get("ok", True):
                job.status = "failed"
            else:
                job.status = "completed"

        job.updated_at = datetime.utcnow().isoformat() + "Z"
        
        # --- MESH SETTLEMENT & STATS ---
        if self.registry:
            mesh_data = job.payload.get("mesh", {})
            worker_id = mesh_data.get("worker_id")
            if worker_id:
                # 1. Arbitrage Settlement
                if job.status == "completed" and self.ledger:
                    try:
                        # Extract payout details
                        payer_id = job.payload.get("payer_id", "default_user")
                        total_cost = float(mesh_data.get("cost", 0))
                        
                        if total_cost > 0:
                            # Governance: Dynamic Margin
                            margin = None
                            worker = self.registry.workers.get(worker_id)
                            if worker:
                                stats = worker.stats
                                # Use calculate_margin helper from ledger
                                if hasattr(self.ledger, '_service') and self.ledger._service:
                                    margin = self.ledger._service.calculate_margin(
                                        stats.success_ema, stats.latency_ms_ema
                                    )
                            
                            success = self.ledger.charge_and_settle(
                                payer_id=payer_id,
                                worker_id=worker_id,
                                total_amount=total_cost,
                                job_id=job_id,
                                margin=margin,
                                note=f"Bridge settlement for job {job_id[:8]}"
                            )
                            if success:
                                margin_pct = f" (margin: {margin*100:.1f}%)" if margin else ""
                                print(f"[bridge] 💰 Settled job {job_id[:8]}: {total_cost} TOK{margin_pct}")
                            else:
                                print(f"[bridge] ⚠️ Settlement failed for job {job_id[:8]} (likely insufficient balance)")
                    except Exception as e:
                        print(f"[bridge] ❌ Error during settlement: {e}")

                # 2. Record Performance Stats
                try:
                    created_dt = datetime.fromisoformat(job.created_at.replace("Z", "+00:00"))
                    now_dt = datetime.now(created_dt.tzinfo)
                    latency_ms = (now_dt - created_dt).total_seconds() * 1000
                    
                    is_ok = job.status == "completed"
                    self.registry.record_worker_result(worker_id, latency_ms, is_ok)
                    print(f"[bridge] 📊 Recorded results for {worker_id}: {latency_ms:.0f}ms, success={is_ok}")
                except Exception as e:
                    print(f"[bridge] Warning: Could not record mesh stats: {e}")
        # -------------------------------

        storage.update_job(job)

        if remove_after_read:
            result_file.unlink(missing_ok=True)

        # NOTE: LCP interpreter call removed from here. 
        # It is now handled centrally in main.py:sync_job to avoid double execution.
        
        return job
