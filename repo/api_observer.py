import os
import numpy as np
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

from core.events import Event
from core.engine import SheratanEngine
from config import CONFIG
from core.policy.loader import load_policy_bundle
from core.policy.gates import compile_gate_config, enforce_env
from core.system.phase1_status import Phase1Status, iso_now

app = FastAPI(title="Sheratan Observer API")

# Unified Engine for Phase 8
engine = SheratanEngine(CONFIG)
current_cycle = 0

class EventInput(BaseModel):
    value: float
    channel: int

def _repo_root() -> Path:
    return Path(__file__).resolve().parent

@app.on_event("startup")
def _startup_phase1():
    repo = _repo_root()
    strict = os.environ.get("PHASE1_STRICT", "1") == "1"
    
    try:
        policy_file = repo / "policies" / "active" / "sheratan-phase1-core.policy.json"
        schema_file = repo / "schemas" / "policy_bundle_v1.json"
        
        policy_file.parent.mkdir(parents=True, exist_ok=True)
        
        if not policy_file.exists():
            default_policy = {
                "policy_id": "sheratan-phase1-core",
                "version": "1.0.0",
                "hash": "sha256:default",
                "rules": [
                    {"rule_id": "deterministic_mode", "type": "require", "target": "DETERMINISTIC_MODE", "value": True}
                ]
            }
            with open(policy_file, "w") as f:
                json.dump(default_policy, f, indent=2)

        bundle = load_policy_bundle(policy_file, schema_file, strict=True)
        cfg = compile_gate_config(bundle)
        enforce_env(cfg, dict(os.environ))
        
        app.state.phase1_status = Phase1Status(
            status="OK",
            reason=None,
            policy_id=bundle.policy_id,
            policy_version=bundle.version,
            policy_hash=bundle.hash,
            deterministic_mode=os.environ.get("DETERMINISTIC_MODE") == "1",
            strict=strict,
            checked_at=iso_now()
        )
    except Exception as e:
        app.state.phase1_status = Phase1Status(
            status="BLOCKED",
            reason=str(e),
            policy_id=None,
            policy_version=None,
            policy_hash=None,
            deterministic_mode=None,
            strict=strict,
            checked_at=iso_now()
        )

@app.get("/health")
def health():
    return {"status": "running", "cycle": current_cycle}

@app.get("/api/system/phase1")
def get_phase1_status():
    return getattr(app.state, "phase1_status", {"status": "BLOCKED", "reason": "Not initialized"})

@app.post("/events")
def post_event(events: List[EventInput]):
    global current_cycle
    
    last_res = 0.0
    for e_in in events:
        event = Event(t=float(current_cycle), source="api", data={"channel": e_in.channel, "value": e_in.value})
        state, res = engine.process_event(event)
        last_res = res
    
    current_cycle += 1
    return {"resonance": last_res, "cycle": current_cycle}

@app.get("/states")
def get_states(min_val: float = 0.1):
    return [
        {
            "id": s.state_id, 
            "value": float(s.weight),
            "score": getattr(s, "current_score", 0.0),
            "recommendation": getattr(s, "recommended_action", None)
        } 
        for s in engine.states if s.weight > min_val
    ]

@app.get("/identity")
def get_identity(top_k: int = 5):
    sorted_states = sorted(engine.states, key=lambda s: s.weight, reverse=True)[:top_k]
    return [
        {
            "state_id": s.state_id,
            "value": float(s.weight),
            "score": getattr(s, "current_score", 0.0)
        }
        for s in sorted_states
    ]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
