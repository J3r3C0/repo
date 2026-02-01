from __future__ import annotations
from pathlib import Path
from typing import Any, Dict
from mesh.core.gates.config import default_gate_config
from mesh.core.gates.pipeline import run_gates_v1, final_decision

def run_dispatch(job: Dict[str, Any], project_root: Path | None = None) -> Dict[str, Any]:
    """
    Standardized Job Dispatcher.
    Runs the G0-G4 gate pipeline and returns a consolidated report.
    """
    # Safe fallback if project_root is not provided
    root = project_root or Path(".")
    cfg = default_gate_config(root)
    reports = run_gates_v1(job, cfg)
    status, action = final_decision(reports)
    
    return {
        "status": status,
        "action": action.value if hasattr(action, 'value') else str(action),
        "reports": [r.__dict__ if hasattr(r, '__dict__') else r for r in reports]
    }

def synthesize_narrative(jid: str) -> Dict[str, Any]:
    """
    Unified View of a job's status and history.
    For now, returns a basic structure.
    """
    return {
        "job_id": jid,
        "narrative": f"Job {jid} is currently being tracked. Detailed synthesis logic is latent.",
        "status": "active"
    }
