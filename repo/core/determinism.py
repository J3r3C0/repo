"""
Determinism Utilities

Provides canonical hashing for input/output to enable:
- Drift detection
- Replay verification
- Regression testing
"""

import json
import hashlib
from typing import Any, Dict


def canonical_json(obj: Any) -> str:
    """
    Convert object to canonical JSON string.
    
    Rules:
    - sort_keys=True (deterministic key order)
    - separators=(',', ':') (no whitespace)
    - ensure_ascii=False (UTF-8)
    """
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def sha256_hash(data: str) -> str:
    """
    Compute SHA-256 hash of string.
    
    Returns: hex digest (64 chars)
    """
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def compute_input_hash(
    job_id: str,
    intent: str,
    action_type: str,
    action_params: Dict[str, Any],
    state_constraints: Dict[str, Any],
    state_context_refs: list
) -> str:
    """
    Compute deterministic input hash.
    
    Input = {job_id, intent, action.type, action.params, state.constraints, state.context_refs}
    """
    input_obj = {
        "job_id": job_id,
        "intent": intent,
        "action_type": action_type,
        "action_params": action_params,
        "state_constraints": state_constraints,
        "state_context_refs": sorted(state_context_refs)  # Sort for determinism
    }
    
    canonical = canonical_json(input_obj)
    return f"sha256:{sha256_hash(canonical)}"


def compute_output_hash(
    status: str,
    score: float,
    metrics: Dict[str, Any],
    error_code: str | None = None,
    artifacts: list | None = None
) -> str:
    """
    Compute deterministic output hash.
    
    Output = {status, score, metrics, error_code?, artifacts}
    """
    output_obj = {
        "status": status,
        "score": round(score, 4),  # Round to avoid float precision issues
        "metrics": {k: round(v, 4) if isinstance(v, float) else v for k, v in metrics.items()},
        "error_code": error_code,
        "artifacts": sorted(artifacts) if artifacts else []  # Sort for determinism
    }
    
    canonical = canonical_json(output_obj)
    return f"sha256:{sha256_hash(canonical)}"
