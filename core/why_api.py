# core/why_api.py
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from .why_reader import latest_event, trace_by_id, traces_by_job_id, stats, sanitize


# IMPORTANT: This module must be READ-ONLY (zero side effects).
# - no writes
# - no priors updates
# - no log mutation

DEFAULT_LOG_PATH = "logs/decision_trace.jsonl"

router = APIRouter(tags=["why"])


@router.get("/latest")
def why_latest(
    intent: Optional[str] = Query(default=None),
    log_path: str = Query(default=DEFAULT_LOG_PATH),
    max_lines: int = Query(default=2000, ge=1, le=200000),
):
    ev, meta = latest_event(log_path, intent=intent, max_lines=max_lines)
    if ev is None:
        return JSONResponse({"ok": False, "error": "not_found", "meta": meta.__dict__}, status_code=404)
    return {"ok": True, "event": sanitize(ev), "meta": meta.__dict__}


@router.get("/trace/{trace_id}")
def why_trace(
    trace_id: str,
    log_path: str = Query(default=DEFAULT_LOG_PATH),
    max_lines: int = Query(default=10000, ge=1, le=500000),
):
    events, meta = trace_by_id(log_path, trace_id=trace_id, max_lines=max_lines)
    if not events:
        return JSONResponse({"ok": False, "error": "not_found", "meta": meta.__dict__}, status_code=404)
    return {"ok": True, "trace_id": trace_id, "events": sanitize(events), "meta": meta.__dict__}


@router.get("/job/{job_id}")
def why_job(
    job_id: str,
    log_path: str = Query(default=DEFAULT_LOG_PATH),
    max_lines: int = Query(default=10000, ge=1, le=500000),
):
    trace_ids, meta = traces_by_job_id(log_path, job_id=job_id, max_lines=max_lines)
    if not trace_ids:
        return JSONResponse({"ok": False, "error": "not_found", "meta": meta.__dict__}, status_code=404)
    return {"ok": True, "job_id": job_id, "trace_ids": trace_ids, "meta": meta.__dict__}


@router.get("/stats")
def why_stats(
    intent: Optional[str] = Query(default=None),
    log_path: str = Query(default=DEFAULT_LOG_PATH),
    window_lines: int = Query(default=10000, ge=1, le=500000),
):
    s, meta = stats(log_path, intent=intent, window_lines=window_lines)
    return {"ok": True, "intent": intent, "stats": s, "meta": meta.__dict__}


# ----------------------------
# Diagnostic Extensions
# ----------------------------

@router.get("/baselines")
def why_baselines(
    metric: Optional[str] = None,
    window: str = "1h",
):
    """Get performance baseline history for metrics."""
    from core.main import baseline_tracker
    
    baselines = baseline_tracker.get_all_baselines(recompute=True)
    
    # Filter by metric if specified
    if metric:
        metric_data = baselines.get("baselines", {}).get(metric, {})
        if not metric_data:
            return JSONResponse(
                {"ok": False, "error": "metric_not_found", "metric": metric},
                status_code=404
            )
        return {
            "ok": True,
            "metric": metric,
            "window": window,
            "baseline": metric_data.get(window, {}),
        }
    
    return {"ok": True, "baselines": baselines}


@router.get("/anomalies")
def why_anomalies(
    window: str = "1h",
    limit: int = 100,
):
    """Get timeline of detected anomalies."""
    from core.main import anomaly_detector
    
    anomalies_data = anomaly_detector.get_anomalies(window=window, limit=limit)
    return {"ok": True, **anomalies_data}


@router.get("/diagnostics")
def why_diagnostics(
    limit: int = 10,
):
    """Get recent diagnostic reports."""
    from core.main import diagnostic_engine
    
    latest = diagnostic_engine.get_latest_report()
    if not latest:
        return JSONResponse(
            {"ok": False, "error": "no_reports"},
            status_code=404
        )
    
    return {
        "ok": True,
        "latest_report": latest,
        "note": "Full diagnostic history not yet implemented"
    }


@router.get("/state-transitions")
def why_state_transitions(
    window: str = "24h",
    limit: int = 50,
):
    """Get state transition patterns and analysis."""
    from core.main import state_machine
    import json
    from pathlib import Path
    
    # Read recent transitions from log
    log_path = Path("logs/state_transitions.jsonl")
    if not log_path.exists():
        return {"ok": True, "transitions": [], "count": 0}
    
    transitions = []
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in lines[-limit:]:
                try:
                    event = json.loads(line.strip())
                    transitions.append(event)
                except:
                    continue
    except Exception as e:
        return JSONResponse(
            {"ok": False, "error": str(e)},
            status_code=500
        )
    
    # Analyze patterns
    total = len(transitions)
    if total == 0:
        return {"ok": True, "transitions": [], "count": 0, "analysis": {}}
    
    # Count transitions by type
    transition_counts = {}
    for t in transitions:
        key = f"{t.get('prev_state', '?')} → {t.get('next_state', '?')}"
        transition_counts[key] = transition_counts.get(key, 0) + 1
    
    # Detect flapping (same transition multiple times)
    flapping = {k: v for k, v in transition_counts.items() if v >= 3}
    
    return {
        "ok": True,
        "count": total,
        "window": window,
        "transitions": transitions,
        "analysis": {
            "transition_counts": transition_counts,
            "flapping_detected": flapping if flapping else None,
            "current_state": state_machine.snapshot().state,
        }
    }
