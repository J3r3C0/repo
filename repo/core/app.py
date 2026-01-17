# repo/core/app.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from pathlib import Path
from core.config import DATA_DIR, BASE_DIR
from core.store import initialize as init_store, create_job as db_create_job, get_all_missions
from core.policy import state_machine, SystemState
from core.models import Job, JobCreate
import time
import json
from fastapi import FastAPI, Request, HTTPException

from core.chain import chain_runner

def create_app() -> FastAPI:
    init_store()
    state_machine.load_or_init()
    chain_runner.start()
    
    app = FastAPI(title="Sheratan Core Evolution")

    @app.get("/api/system/health")
    async def health():
        snap = state_machine.snapshot()
        return {
            "status": "ok" if snap["state"] == "OPERATIONAL" else "ready",
            "wal": True, 
            "db": "operational",
            "state": snap["state"]
        }

    @app.get("/api/system/state")
    async def get_system_state():
        snap = state_machine.snapshot()
        state_duration = time.time() - snap["since_ts"]
        return {
            "state": snap["state"],
            "since": snap["since_ts"],
            "duration_sec": int(state_duration),
            "counters": snap.get("counters", {}),
            "last_transition": snap.get("last_transition")
        }

    @app.post("/api/system/state/transition")
    async def transition_system_state(payload: dict):
        next_state_str = payload.get("state")
        reason = payload.get("reason")
        actor = payload.get("actor", "user")
        
        if not next_state_str or not reason:
            raise HTTPException(400, "Missing 'state' or 'reason'")
        
        try:
            next_state = SystemState(next_state_str)
            event = state_machine.transition(next_state, reason=reason, actor=actor, meta=payload.get("meta"))
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
        log_path = state_machine.log_path
        if not log_path.exists():
            return []
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            recent = lines[-limit:] if len(lines) > limit else lines
            return [json.loads(line.strip()) for line in recent]
        except Exception:
            return []

    @app.get("/api/missions")
    async def list_missions():
        return [m.dict() for m in get_all_missions()]

    @app.post("/api/jobs")
    async def create_job(payload: dict):
        kind = payload.get("kind", "unknown")
        params = payload.get("params", {})
        
        # 1. Create Job Model
        jc = JobCreate(payload=params)
        job = Job.from_create(task_id="exercise-task", j=jc)
        job.kind = kind
        
        # 2. Dynamic Plugin Execution
        import importlib
        try:
            module = importlib.import_module(f"plugins.{kind}")
            plugin_result = module.handle(params)
            job.result = json.dumps(plugin_result)
            job.status = "completed" if plugin_result.get("ok") else "failed"
        except ImportError:
            job.status = "failed"
            job.result = json.dumps({"ok": False, "error": f"Plugin {kind} not found"})
        except Exception as e:
            job.status = "failed"
            job.result = json.dumps({"ok": False, "error": str(e)})
        
        # 3. Finalize in DB
        db_create_job(job)
        return {"ok": job.status == "completed", "job_id": job.id, "result": json.loads(job.result)}

    @app.get("/index.html")
    @app.get("/")
    async def serve_index():
        index_path = BASE_DIR / "ui" / "dist" / "index.html"
        if index_path.exists():
            return HTMLResponse(content=index_path.read_text())
        return HTMLResponse(content="<html><body>Sheratan Evolution Mock UI</body></html>")

    return app
