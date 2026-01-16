# core/idempotency.py
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, Optional, Literal, Tuple


Action = Literal["ALLOW_NEW", "RETURN_EXISTING", "REJECT"]


@dataclass(frozen=True)
class IdempotencyDecision:
    """
    Action meanings:
      - ALLOW_NEW: proceed with creating a new job (no idempotency key, or key unused)
      - RETURN_EXISTING: return existing job_id/status (and cached_result if available)
      - REJECT: same key used with different payload (409 Conflict)
    """
    action: Action
    job_id: Optional[str] = None
    reason: str = ""
    payload_hash: Optional[str] = None
    cached_result: Optional[Dict[str, Any]] = None


def canonical_json(obj: Any) -> str:
    """
    Canonical JSON for stable hashing.
    - sort_keys=True: stable key order
    - separators=(',', ':'): no whitespace
    - ensure_ascii=False: stable UTF-8 representation
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def compute_payload_hash(payload: Dict[str, Any]) -> str:
    return sha256_hex(canonical_json(payload))


def evaluate_idempotency(
    storage: Any,
    *,
    idempotency_key: Optional[str],
    payload: Dict[str, Any],
) -> IdempotencyDecision:
    """
    Storage contract (minimal):
      - storage.find_job_by_idempotency_key(key) -> job|None
        job fields used here (attribute or dict):
          - id / job_id (string)
          - status (string)
          - idempotency_hash (string or None)
          - completed_result (json string or dict or None)
      - (optional) storage.get_cached_result(job_id) -> dict|None
        If not present, we attempt to read completed_result from job itself.

    Rules:
      - No key: ALLOW_NEW
      - Same key + Same payload_hash: RETURN_EXISTING
      - Same key + Different payload_hash: REJECT (collision)
    """
    key = (idempotency_key or "").strip()
    if not key:
        return IdempotencyDecision(action="ALLOW_NEW", reason="no_key")

    payload_hash = compute_payload_hash(payload)

    existing = storage.find_job_by_idempotency_key(key)
    if not existing:
        return IdempotencyDecision(
            action="ALLOW_NEW",
            reason="key_unused",
            payload_hash=payload_hash,
        )

    # Support both dict-like and attribute-like objects
    def _get(obj: Any, name: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    existing_hash = _get(existing, "idempotency_hash")
    job_id = _get(existing, "job_id") or _get(existing, "id") or _get(existing, "jobId")
    status = _get(existing, "status", "")

    # If legacy rows exist without stored hash, treat as collision-safe:
    # Only allow return_existing if payload_hash matches after we set it later.
    # Here we must be conservative: missing stored hash => reject only if you want strictness.
    # For v2.9: default to "RETURN_EXISTING" only if hash matches; otherwise REJECT if hash differs.
    if existing_hash and existing_hash != payload_hash:
        return IdempotencyDecision(
            action="REJECT",
            job_id=job_id,
            reason="collision_different_payload",
            payload_hash=payload_hash,
        )

    # Return cached result if job is completed and cached_result exists
    cached: Optional[Dict[str, Any]] = None

    # Try explicit storage getter first
    get_cached = getattr(storage, "get_cached_result", None)
    if callable(get_cached) and job_id:
        try:
            cached = get_cached(job_id)
        except Exception:
            cached = None

    # Fallback: check completed_result on the job row
    if cached is None:
        cr = _get(existing, "completed_result")
        if isinstance(cr, dict):
            cached = cr
        elif isinstance(cr, str) and cr.strip():
            try:
                cached = json.loads(cr)
            except Exception:
                cached = None

    return IdempotencyDecision(
        action="RETURN_EXISTING",
        job_id=job_id,
        reason=f"dedup_existing_status:{status or 'unknown'}",
        payload_hash=payload_hash,
        cached_result=cached,
    )


def build_idempotency_conflict_detail(
    idempotency_key: str,
    *,
    existing_job_id: Optional[str],
    existing_hash_prefix: Optional[str],
    new_hash_prefix: str,
) -> Dict[str, Any]:
    """
    Helper for HTTP 409 responses (sanitized).
    Avoids leaking full hashes / payloads.
    """
    return {
        "error": "IDEMPOTENCY_KEY_COLLISION",
        "idempotency_key": idempotency_key,
        "existing_job_id": existing_job_id,
        "existing_hash_prefix": existing_hash_prefix,
        "new_hash_prefix": new_hash_prefix,
    }
