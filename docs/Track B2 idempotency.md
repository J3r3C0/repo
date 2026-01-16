Perfekt. Dann **B2 Skeleton – sauber, minimal-invasiv, anschlussfähig an euren Stand (B1 + Dispatcher-Modell)**.

Ich halte das bewusst als **Implementierungs-Skeleton + klare Contracts**, nicht als „fertigen Code“, damit ihr kontrolliert weiterbauen könnt.

---

# Track B2 — Idempotency

**Skeleton v1 (anschlussfähig an `RESUME_CONTEXT_v2.9.md`)**

## Ziel (nochmal präzise)

> **At-most-once Semantik für Job-Create**, ohne den Dispatcher umzubauen.

* gleiche Anfrage ≠ doppelter Job
* Kollisionen sichtbar & auditierbar
* keine Seiteneffekte für bestehende Jobs

---

## 1️⃣ Datenmodell (minimal)

### Erweiterung `jobs` Tabelle

*(SQLite / core/database.py Migration)*

```sql
ALTER TABLE jobs ADD COLUMN idempotency_key TEXT;
ALTER TABLE jobs ADD COLUMN idempotency_hash TEXT;
ALTER TABLE jobs ADD COLUMN completed_result TEXT;
ALTER TABLE jobs ADD COLUMN idempotency_first_seen_utc TEXT;
```

**Konventionen**

* `idempotency_key`: vom Client / ChainSpec
* `idempotency_hash`: SHA256(canonical_payload)
* `completed_result`: JSON (minimal)
* **kein UNIQUE constraint** → Logik bleibt im Storage (kontrollierbar)

---

## 2️⃣ Storage Layer (core/storage.py)

### Neue Helper (Skeleton)

```python
def find_job_by_idempotency(key: str):
    """Return job row or None"""

def register_idempotency(key: str, payload_hash: str, now_utc: str):
    """Insert placeholder / metadata"""

def check_idempotency_collision(existing_job, payload_hash: str) -> bool:
    """True if same key but different payload"""

def cache_completed_result(job_id: str, result: dict):
    """Store minimal completion result"""

def get_cached_result(job_id: str):
    """Return cached minimal result or None"""
```

**Wichtig**

* Alles **atomar** (transaktional)
* Kein Dispatcher-Wissen hier

---

## 3️⃣ Idempotency Gate (core/idempotency.py – NEW)

```python
class IdempotencyDecision(NamedTuple):
    action: Literal["ALLOW_NEW", "RETURN_EXISTING", "REJECT"]
    job_id: Optional[str]
    cached_result: Optional[dict]
    reason: str
```

```python
def evaluate_idempotency(
    idempotency_key: Optional[str],
    payload: dict,
    now_utc: str,
) -> IdempotencyDecision:
    """
    Rules:
    - No key → ALLOW_NEW
    - Same key + same hash → RETURN_EXISTING
    - Same key + different hash → REJECT (409)
    """
```

Canonical Hash:

```python
payload_hash = sha256(canonical_json(payload))
```

---

## 4️⃣ Integration Point (core/main.py)

### **Job Create Flow**

*(exakter Ort: dort wo Job in DB geschrieben wird)*

Pseudocode:

```python
decision = evaluate_idempotency(key, payload, now)

if decision.action == "REJECT":
    audit("IDEMPOTENCY_KEY_COLLISION", ...)
    raise HTTPException(409)

if decision.action == "RETURN_EXISTING":
    return {
        "job_id": decision.job_id,
        "status": existing.status,
        "result": decision.cached_result,
        "idempotent": True,
    }

# else: ALLOW_NEW
job_id = create_job(...)
register_idempotency(...)
return {"job_id": job_id, "status": "accepted"}
```

🚫 **Kein Dispatcher-Code anfassen**

---

## 5️⃣ Completion Hook (minimal)

Beim Job-Finish (wo Status → completed):

```python
if job.idempotency_key:
    cache_completed_result(job.id, {
        "ok": True,
        "result_id": job.result_id
    })
```

---

## 6️⃣ Audit & Metrics

### Audit Events

* `IDEMPOTENT_HIT`
* `IDEMPOTENCY_KEY_COLLISION`

(JSONL wie bisher)

### Metrics

* `idempotent_hits_1m`
* `idempotent_collisions_1m`

---

## 7️⃣ Verification Skeleton

`scripts/verify_b2_idempotency.ps1`

### Tests

**T1 – Dedup**

```
POST job (key=A, payload=X)
POST job (key=A, payload=X)
→ same job_id
```

**T2 – Collision**

```
POST job (key=A, payload=X)
POST job (key=A, payload=Y)
→ 409 + audit
```

**T3 – Completion Cache**

```
POST job (key=A)
wait completed
POST job (key=A)
→ returns cached result
```

**T4 – No key**

```
POST job (no key)
POST job (no key)
→ 2 different jobs
```

---

## 8️⃣ Nicht-Ziele (bewusst)

* ❌ kein Retry-Rewrite (macht B1)
* ❌ kein Dispatcher-Block
* ❌ kein Hard-Enforcement
* ❌ keine TTL-Eviction (optional B2.1)

---

## Status nach diesem Skeleton

Wenn das umgesetzt ist:

* **B2 = funktional abgeschlossen**
* **B3 (Result Integrity)** kann exakt hier andocken
* Architektur bleibt **lesbar & kontrollierbar**

---

👉 **Nächster Schritt**
Wenn du willst, gehe ich als Nächstes:

* **File-by-file Patch Reihenfolge** *(commit-safe)*

* **direkt `core/idempotency.py` als Startfile schreiben*


