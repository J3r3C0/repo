# core/result_integrity.py
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple, Literal


HASH_ALG_DEFAULT: Literal["sha256"] = "sha256"


class IntegrityError(Exception):
    """Raised when integrity verification fails (hash mismatch or invalid input)."""


@dataclass(frozen=True)
class IntegrityStatus:
    """
    - ok: verification passed (or computed and stored)
    - migrated: hash was missing and has been computed (soft migrate)
    - expected_hash: hash stored / expected
    - actual_hash: hash computed from the current result payload
    - alg: hashing algorithm used
    """
    ok: bool
    migrated: bool
    expected_hash: Optional[str]
    actual_hash: str
    alg: str


def canonical_json(obj: Any) -> str:
    """
    Canonical JSON used for hashing.
    Must remain stable across versions:
      - sort_keys=True
      - separators=(',', ':') (no whitespace)
      - ensure_ascii=False (UTF-8)
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def compute_result_hash(result_obj: Dict[str, Any], alg: str = HASH_ALG_DEFAULT) -> str:
    if alg != "sha256":
        raise ValueError(f"Unsupported hash algorithm: {alg}")
    canon = canonical_json(result_obj)
    return sha256_hex(canon)


def verify_or_migrate_hash(
    *,
    result_obj: Dict[str, Any],
    expected_hash: Optional[str],
    alg: str = HASH_ALG_DEFAULT,
    # If provided, called when expected_hash is missing to persist the newly computed hash (soft migrate).
    persist_hash: Optional[Callable[[str, str], None]] = None,
    # If provided, called when expected_hash is missing to persist canonical JSON (optional; for debugging).
    persist_canonical: Optional[Callable[[str], None]] = None,
) -> IntegrityStatus:
    """
    Policy B: compute-on-first-read (soft migrate)
      - If expected_hash is missing:
          compute actual_hash, return ok=True migrated=True,
          and (optionally) persist via callbacks.
      - If expected_hash exists:
          compute and compare; mismatch => IntegrityError

    persist_hash(actual_hash, alg) signature:
      - actual_hash: computed hash string
      - alg: algorithm string (e.g., "sha256")

    persist_canonical(canon_json) signature:
      - canon_json: canonical JSON string used to compute the hash
    """
    if not isinstance(result_obj, dict):
        raise IntegrityError("Result object must be a dict")

    if alg != "sha256":
        raise IntegrityError(f"Unsupported hash algorithm: {alg}")

    canon = canonical_json(result_obj)
    actual_hash = sha256_hex(canon)

    # Missing hash => soft migrate
    if not expected_hash:
        if persist_canonical:
            try:
                persist_canonical(canon)
            except Exception:
                # Never block read on persistence issues in soft-migrate mode
                pass

        if persist_hash:
            try:
                persist_hash(actual_hash, alg)
            except Exception:
                # Never block read on persistence issues in soft-migrate mode
                pass

        return IntegrityStatus(
            ok=True,
            migrated=True,
            expected_hash=None,
            actual_hash=actual_hash,
            alg=alg,
        )

    # Hash present => strict verify
    if expected_hash != actual_hash:
        raise IntegrityError("RESULT_INTEGRITY_FAIL")

    return IntegrityStatus(
        ok=True,
        migrated=False,
        expected_hash=expected_hash,
        actual_hash=actual_hash,
        alg=alg,
    )
