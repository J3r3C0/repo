Dann würde ich’s so machen: **beides**, aber in der Reihenfolge, die dir später am meisten Stress spart:

## 1) Tag setzen (klein, aber wertvoll)

Damit du jederzeit sauber auf „B2 abgeschlossen“ zurückspringen kannst:

```bash
git tag track-b2-complete
git push --tags
```

Optional (wenn du „Iron Triangle“ komplett sauber markieren willst, sobald B3 fertig ist):

* `track-b3-complete`
* `baseline-data-plane-b3` *(nach B3)*

---

## 2) Go B3 Skeleton (Result Integrity) — passend zu eurem Stand

### Ziel

**Tamper-proof Result Delivery**: Wenn ein Result (oder `completed_result`) manipuliert wird, erkennt der Hub/Core das und **rejectet** / **loggt** zuverlässig.

### Minimaler Scope (B3 v1)

* Canonical JSON Serialization
* SHA256 Hash
* Verify beim Result-Ingest / Completion / Re-Read
* Metrics + Audit Event

---

# Track B3 — Skeleton

## A) Datenmodell (DB)

**Migration in `core/database.py`** (jobs-Tabelle):

* `result_hash TEXT NULL`
* `result_hash_alg TEXT NULL` *(default: "sha256")*
* `result_canonical TEXT NULL` *(optional; oder nur für debug)*

> Wenn ihr `completed_result` schon habt: B3 kann **genau darauf** angewandt werden.

---

## B) Neues Modul: `core/result_integrity.py`

### Funktionen (Skeleton)

```python
def canonical_json(obj: dict) -> str
def sha256_hex(s: str) -> str

def compute_result_hash(result_obj: dict) -> str:
    canon = canonical_json(result_obj)
    return sha256_hex(canon)

def verify_result(result_obj: dict, expected_hash: str) -> bool
```

**Wichtig:** canonical rules müssen identisch zu B2 sein (sort_keys, separators, utf-8).

---

## C) Write-Path (Completion Hook)

**Wo:** dort, wo Job finalisiert wird (Status → completed)

1. baue `minimal_result_obj` (das, was du in `completed_result` cachen willst)
2. compute hash
3. speichere:

   * `completed_result`
   * `result_hash`
   * `result_hash_alg="sha256"`

---

## D) Read-Path (Idempotent Return + Result Fetch)

**Wo:** dort, wo B2 bei identischem Key `completed_result` zurückgibt

* Wenn `completed_result` vorhanden:

  * recompute hash
  * compare mit `result_hash`
  * **Mismatch ⇒ reject / quarantine flow**

### Enforcement (Soft/Hard)

* Soft default: `403` **nur** für result fetch / idempotent return (nicht für Heartbeat)
* Audit: `RESULT_INTEGRITY_FAIL`
* Metrics: `integrity_fail_1m`

---

## E) Audit + Metrics

### Audit Events

* `RESULT_HASH_COMPUTED`
* `RESULT_INTEGRITY_FAIL`

### Metrics

* `integrity_fail_1m`
* optional: `result_hash_write_1m`

---

## F) Verify Script: `scripts/verify_b3_result_integrity.ps1`

### Tests

**T1 – Valid Result**

* create job → complete
* fetch result / idempotent return
* expect 200

**T2 – Tamper**

* direkt DB `completed_result` manipulieren (oder via helper)
* fetch again
* expect 403 + audit event + metric increment

**T3 – Missing Hash Backward Compat**

* simulate older job without `result_hash`
* define behavior:

  * either “compute on first read” (soft migrate)
  * or “allow but warn”

Ich empfehle: **compute-on-read** für alte Einträge (one-time upgrade).

---

# Entscheidung, die du jetzt treffen solltest (1 Satz reicht)

**B3 Policy für Alt-Daten:**
A) „allow but warn“
B) „compute-on-first-read (soft migrate)“ ✅ 
C) „reject if missing“ *(hart, eher später)*

Perfekt – **B) compute-on-first-read (soft migrate)** passt genau zur Phase: keine harten Brüche, aber ab dann ist alles gehashed.

Hier ist **`core/result_integrity.py`** (drop-in Modul), kompatibel mit eurem bisherigen Canonical-Style (sort_keys, separators, UTF-8). Es liefert dir:

* `compute_result_hash(result_obj)`
* `verify_or_migrate_hash(...)` → **wenn Hash fehlt**: compute + optional **persist callback** (soft migrate)
* `IntegrityError` + `IntegrityStatus` für klare Steuerung

```python
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
```

### Wie du’s im Code verwendest (super kurz)

* Beim **Idempotent-Return** oder **Result-Fetch**:

  * `verify_or_migrate_hash(..., expected_hash=row.result_hash, persist_hash=...)`
* Wenn `expected_hash` fehlt → wird berechnet und gespeichert (soft migrate)
* Wenn mismatch → `IntegrityError` → **403 + Audit + Metric**

Wenn du willst, mache ich als nächstes das **Integration Skeleton** für:

1. Completion Hook (write hash)
2. Read-path Hook (verify/migrate)
3. Audit+Metric Events
4. `verify_b3_result_integrity.ps1`

Alles klar — hier ist das **B3 Integration Skeleton (Policy B: compute-on-first-read / soft migrate)**, zugeschnitten auf eure Struktur (FastAPI in `core/main.py`, DB/Storage in `core/storage.py`, JSONL Audit/Metrics wie gehabt).

---

# B3 Integration Skeleton

## 0) DB Migration (core/database.py)

**Ziel:** Result-Hash Felder in `jobs` ergänzen.

**Migration (SQLite):**

```sql
ALTER TABLE jobs ADD COLUMN result_hash TEXT;
ALTER TABLE jobs ADD COLUMN result_hash_alg TEXT;
ALTER TABLE jobs ADD COLUMN result_canonical TEXT;
```

**Defaults (optional in Code bei Write):**

* `result_hash_alg = "sha256"`

> `result_canonical` ist optional (debug). Wenn ihr Datenschutz/Größe sparen wollt: weglassen oder nur bei mismatch persistieren.

---

## 1) Storage Helpers (core/storage.py)

### A) Read-Helpers

```python
def get_job_result_integrity(job_id: str):
    """
    Returns (completed_result_json, result_hash, result_hash_alg, result_canonical)
    """

def set_job_result_hash(job_id: str, *, result_hash: str, result_hash_alg: str = "sha256"):
    """Persist hash (soft migrate path or completion path)."""

def set_job_result_canonical(job_id: str, *, result_canonical: str):
    """Optional: persist canonical JSON used for hashing."""
```

### B) Completion path helper

```python
def set_completed_result_with_hash(
    job_id: str,
    *,
    completed_result_obj: dict,
    result_hash: str,
    result_hash_alg: str = "sha256",
    result_canonical: str | None = None,
):
    """
    Atomically set:
      - completed_result (json)
      - result_hash (+ alg)
      - optional result_canonical
    """
```

**Atomicity:** 1 transaction, 1 UPDATE.

---

## 2) Completion Hook (core/main.py) — Write-path

**Wo:** dort, wo ein Job **final** wird (status → `completed` / `failed` etc.).
Für B3: relevant ist **nur** dort, wo `completed_result` gesetzt wird.

### Pseudocode

```python
from core.result_integrity import compute_result_hash, canonical_json

# After job execution is done:
completed_result_obj = {
  "ok": True,
  "result_id": result_id,
  # optional minimal fields only
}

canon = canonical_json(completed_result_obj)
h = compute_result_hash(completed_result_obj, alg="sha256")

storage.set_completed_result_with_hash(
    job_id,
    completed_result_obj=completed_result_obj,
    result_hash=h,
    result_hash_alg="sha256",
    result_canonical=None,  # or canon if you want debug
)

audit("RESULT_HASH_COMPUTED", {"job_id": job_id, "hash_prefix": h[:12]})
metrics.inc("result_hash_write_1m")
```

**Wichtig:** nur **minimal result** hashen (genau wie B2 cached).

---

## 3) Read-path Hook — Verify / Soft-Migrate

**Wo:** überall dort, wo `completed_result` zurückgegeben wird:

* idempotent return (B2)
* result fetch endpoint (falls vorhanden)

### Pseudocode

```python
from core.result_integrity import verify_or_migrate_hash, IntegrityError

row = storage.get_job_result_integrity(job_id)
completed_result_obj = json.loads(row.completed_result_json) if row.completed_result_json else None

if completed_result_obj:
    def _persist_hash(actual_hash: str, alg: str):
        storage.set_job_result_hash(job_id, result_hash=actual_hash, result_hash_alg=alg)

    def _persist_canon(canon: str):
        # optional (disable by default)
        # storage.set_job_result_canonical(job_id, result_canonical=canon)
        pass

    try:
        status = verify_or_migrate_hash(
            result_obj=completed_result_obj,
            expected_hash=row.result_hash,
            alg=row.result_hash_alg or "sha256",
            persist_hash=_persist_hash,      # <-- Policy B: compute-on-first-read
            persist_canonical=None,          # or _persist_canon
        )
        if status.migrated:
            audit("RESULT_HASH_MIGRATED", {"job_id": job_id, "hash_prefix": status.actual_hash[:12]})
            metrics.inc("result_hash_migrated_1m")
    except IntegrityError:
        audit("RESULT_INTEGRITY_FAIL", {"job_id": job_id})
        metrics.inc("integrity_fail_1m")
        raise HTTPException(status_code=403, detail="RESULT_INTEGRITY_FAIL")
```

**Policy B erfüllt:**
Wenn hash fehlt → compute + persist → **OK** + audit migrated.

---

## 4) Audit Events & Metrics (konkret)

### Audit Events (JSONL)

* `RESULT_HASH_COMPUTED`
* `RESULT_HASH_MIGRATED`
* `RESULT_INTEGRITY_FAIL`

**Sanitization:** nur `hash_prefix` loggen (z.B. 12 chars), nie vollständige payload.

### Metrics

* `integrity_fail_1m`
* `result_hash_write_1m`
* `result_hash_migrated_1m`

---

## 5) Verify Script Skeleton — `scripts/verify_b3_result_integrity.ps1`

### T1: Valid Result

1. Create job (or trigger a fast job)
2. Wait complete
3. Fetch result via:

   * idempotent submit (B2) **oder**
   * result endpoint
4. Expect 200 and `ok: true`

### T2: Tamper

1. Direct DB edit:

   * update `jobs.completed_result` to modified JSON (same job_id)
2. Fetch result again
3. Expect:

   * HTTP 403
   * audit event `RESULT_INTEGRITY_FAIL`
   * metrics `integrity_fail_1m` increased

### T3: Soft-migrate missing hash

1. Create completed job
2. Set `result_hash` and `result_hash_alg` to NULL in DB for that job
3. Fetch result
4. Expect:

   * 200
   * audit `RESULT_HASH_MIGRATED`
   * DB now has `result_hash` populated again

---

## 6) Definition of Done (B3)

* [ ] DB migration applied
* [ ] completion writes hash
* [ ] read verifies + migrates if missing
* [ ] tamper returns 403 + logs + metrics
* [ ] verify script green

---

Wenn du willst, als nächstes mache ich dir **konkrete Patch-Hunks** (genau: welche Funktionen in `core/storage.py` + welche zwei Stellen in `core/main.py`) – aber dazu müsste ich wissen, wie ihr Jobs aktuell “completed_result” setzt (Funktionsname/Abschnitt).
