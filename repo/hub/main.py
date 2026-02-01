from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Request, Depends
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
import sys
import os
from pathlib import Path
from typing import List, Optional, Dict, Any

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.config import DATA_DIR
from hub import models, storage, dispatcher, orchestrator, why_api
from core.engine import SheratanEngine

# --- Hub Configuration ---
class HubConfig:
    WINDOW_SIZE = 1000
    DEFAULT_WEIGHT = 1.0
    DEFAULT_DECAY = 0.95
    max_active_states = 1000
    MAX_SEGMENT_AGE = 1000

# Initialize System Components
engine = SheratanEngine(HubConfig) # Direct engine access for unified API
orch = orchestrator.SheratanOrchestrator(HubConfig)
# Bridge would normally come from webrelay_bridge, dummy for now if webrelay not needed for boot
# In reality, we'd initialize bridge here.
from hub.webrelay_bridge import WebRelayBridge
bridge = WebRelayBridge(DATA_DIR / "webrelay_out", DATA_DIR / "webrelay_in")
disp = dispatcher.Dispatcher(bridge, lcp=None, orchestrator=orch)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[hub] Agency & Orchestration Online")
    disp.start()
    yield
    disp.stop()
    print("[hub] Hub Shutdown")

app = FastAPI(
    title="Sheratan Hub",
    description="Agency & Orchestration API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Include routers ---
app.include_router(why_api.router, prefix="/api/why")

# --- Agency Endpoints ---

@app.get("/health")
@app.get("/api/health")
async def get_health():
    return {"status": "ok", "service": "hub", "time": datetime.now(timezone.utc).isoformat()}

@app.get("/api/status")
async def get_status():
    return {
        "ok": True,
        "missions": len(storage.list_missions()),
        "pending_jobs": storage.count_pending_jobs(),
        "inflight_jobs": storage.count_inflight_jobs()
    }

@app.get("/api/missions", response_model=List[models.Mission])
async def list_missions():
    return storage.list_missions()

@app.post("/api/missions", response_model=models.Mission)
async def create_mission(m: models.MissionCreate):
    mission = models.Mission.from_create(m)
    return storage.create_mission(mission)

@app.get("/api/missions/{mission_id}")
async def get_mission(mission_id: str):
    m = storage.get_mission(mission_id)
    if not m: raise HTTPException(status_code=404, detail="mission_not_found")
    return m

@app.post("/api/missions/{mission_id}/tasks", response_model=models.Task)
async def create_task(mission_id: str, t: models.TaskCreate):
    task = models.Task.from_create(mission_id, t)
    return storage.create_task(task)

@app.post("/api/tasks/{task_id}/jobs", response_model=models.Job)
async def create_job(task_id: str, j: models.JobCreate):
    job = models.Job.from_create(task_id, j)
    return storage.create_job(job)

@app.get("/api/jobs/{job_id}", response_model=models.Job)
async def get_job(job_id: str):
    j = storage.get_job(job_id)
    if not j: raise HTTPException(status_code=404, detail="job_not_found")
    return j

# --- Perception Proxies (Direct integration) ---

@app.post("/api/event")
async def post_event(payload: dict):
    events = payload.get("events", [])
    if not events: return {"ok": False, "error": "empty"}
    return {"ok": True, "resonances": engine.process_events(events)}

@app.get("/api/state")
async def get_state():
    states = engine.get_state_snapshot()
    state_hash = engine.memory.get_state_hash()
    return {"ok": True, "state_hash": state_hash, "states": states}

@app.get("/api/identity")
async def get_identity(threshold: float = 0.5, top_k: int = 10):
    from core.identity import select_top_states
    states = engine.get_state_snapshot()
    selected = select_top_states(
        states, threshold=threshold, top_k=top_k, 
        current_cycle=engine.cycle_count,
        last_selected_segments=getattr(engine, "_last_selected", set())
    )
    engine._last_selected = {int(s["segment"]) for s in selected}
    return {"ok": True, "selected_states": selected}

@app.get("/")
def root():
    return {"sheratan": "active", "mode": "unified_hub"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
