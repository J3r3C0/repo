"""core/envelope.py

Canonical schema normalisation.

Sheratan has multiple internal representations of a "job":
 - persisted DB Job model (models.Job)
 - gate input shape (mesh gates)
 - WebRelay job files

To prevent schema drift, we define a *single* canonical envelope that is
DecisionTrace-like and stable.

This module provides small helpers to:
 - build a JobEnvelope v1 (or JobEnvelope-lite) from DB objects
 - build a ResultEnvelope v1 from raw worker outputs

The goal is *not* to force every internal subsystem to store the envelope,
but to ensure external boundaries (gates, relays, workers) always see a
stable shape.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, Optional


def _iso_now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def build_job_envelope_v1(
    *,
    job_id: str,
    kind: str,
    params: Optional[Dict[str, Any]] = None,
    mission_id: Optional[str] = None,
    task_id: Optional[str] = None,
    chain_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    source_zone: str = "internal",
    build_id: str = "main-v2",
    node_id: Optional[str] = None,
    identity: Optional[str] = None,
    priority: str = "normal",
    risk: str = "low",
    gates_profile: str = "default",
) -> Dict[str, Any]:
    """Create a canonical JobEnvelope v1 dict.

    NOTE: This is intentionally conservative and does not require the whole
    mission/task objects. Those may be attached as *payload* for legacy consumers.
    """
    if params is None:
        params = {}

    return {
        "schema_version": "job_envelope_v1",
        "job_id": job_id,
        "mission_id": mission_id,
        "task_id": task_id,
        # intent is semantic; keep it equal to kind for now to avoid forcing new taxonomy
        "intent": kind,
        "action": {
            "kind": kind,
            "params": params,
            "capabilities": [kind],
            "requires": {
                "source_zone": source_zone,
                "paths": [],
                "network": False,
                "llm": False,
            },
        },
        "provenance": {
            "source_zone": source_zone,
            "created_at": _iso_now(),
            "created_by": {"node_id": node_id, "identity": identity},
            "build_id": build_id,
        },
        "policy_context": {
            "priority": priority,
            "risk": risk,
            "gates_profile": gates_profile,
        },
        "refs": {
            "trace_id": trace_id,
            "chain_id": chain_id,
        },
    }


def build_result_envelope_v1(
    *,
    job_id: str,
    ok: bool,
    status: str,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[Dict[str, Any]] = None,
    trace_id: Optional[str] = None,
    why_ref: Optional[str] = None,
    started_at: Optional[str] = None,
    completed_at: Optional[str] = None,
) -> Dict[str, Any]:
    if result is None:
        result = {}
    if error is None:
        error = {}
    if completed_at is None:
        completed_at = _iso_now()

    return {
        "schema_version": "result_envelope_v1",
        "job_id": job_id,
        "ok": bool(ok),
        "status": status,
        "error": error,
        "result": {
            "summary": result.get("summary", ""),
            "data": result.get("data", result),
        },
        "evidence": {
            "artifacts": [],
            "logs": [],
            "metrics": {},
        },
        "decision": {
            "trace_id": trace_id,
            "why_ref": why_ref,
        },
        "timing": {
            "started_at": started_at,
            "completed_at": completed_at,
        },
    }
