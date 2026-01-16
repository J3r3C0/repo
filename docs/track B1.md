Alles klar — dann skizzieren wir **Track B1 (Backpressure & Retry Budgets)** direkt so, dass du daraus **sofort patchen** kannst (ohne Pull-Endpoint, passend zu eurem Push/Dispatcher/WebRelayBridge-Flow).

# Track B1 — Skizze (v2.9) Backpressure im Push/Dispatcher-Core

## Ziel

Unter Last sollen Jobs **nicht unkontrolliert wachsen**, sondern:

* **Queue Depth** begrenzen (Drop/Defer)
* **Inflight** begrenzen (Sättigung → warten)
* **Retry Budgets** verhindern „Retry-Stürme“
* Alles **messbar** (Metrics) und **auditierbar** (Events)

---

# B1.1 Konfiguration (Defaults + ENV)

**New/Modify:** `core/config.py` (oder wo ihr ENV lest)

Empfohlene ENV Keys:

* `SHERATAN_MAX_QUEUE_DEPTH=1000`
* `SHERATAN_MAX_INFLIGHT=100`
* `SHERATAN_LEASE_TIMEOUT_SEC=300`
* `SHERATAN_RETRY_MAX_ATTEMPTS=5`
* `SHERATAN_RETRY_BASE_DELAY_MS=500`
* `SHERATAN_BACKPRESSURE_MODE=drop|defer` *(default: defer für Sicherheit)*

---

# B1.2 Datenmodell (minimal, SQLite)

Ihr habt Push/Dispatcher. Deshalb Backpressure dort, wo Jobs **entstehen** und **dispatcht** werden.

## Option A (empfohlen): In DB (robust)

**Modify:** `core/database.py`

Ergänze in eurer `jobs` Tabelle (falls vorhanden) oder in eurer Dispatch-Queue Tabelle:

* `status` (pending|inflight|done|failed)
* `lease_owner` TEXT NULL
* `lease_until_utc` TEXT NULL
* `attempts` INTEGER DEFAULT 0
* `next_retry_utc` TEXT NULL
* `created_utc` TEXT
* `updated_utc` TEXT

Wenn ihr *schon* `jobs` habt: nur fehlende Columns als migration hinzufügen (wie bei A3).

---

# B1.3 Storage Helpers

**Modify:** `core/storage.py`

### 1) Queue depth & inflight counts

* `count_pending_jobs() -> int`
* `count_inflight_jobs() -> int`
* `count_ready_jobs(now) -> int` *(pending und retry-time erreicht)*

### 2) Claim/Lease Mechanismus (Inflight)

* `lease_next_job(worker_id, now) -> job|None`

  * atomar: wählt 1 job `pending`/`ready` und setzt `inflight + lease_until`
* `reap_expired_leases(now) -> int`

  * inflight jobs mit `lease_until < now` → zurück auf `pending` + audit event

### 3) Retry Budget

* `schedule_retry(job_id, attempts, now)`:

  * wenn `attempts >= MAX`: `failed`
  * sonst `next_retry_utc = now + backoff(attempts)` und status bleibt pending

> Wichtig: Das macht Retry “zeitlich verteilt”, statt sofort.

---

# B1.4 Dispatcher Gate (Backpressure)

**Modify:** `core/main.py` (Dispatcher Loop / Job Creation)

## Gate 1: Beim Job-Erstellen (Queue Depth)

Wenn neue Jobs erzeugt werden:

* `pending = count_pending_jobs()`
* wenn `pending >= MAX_QUEUE_DEPTH`:

  * Mode `defer`: **nicht erzeugen**, sondern „defer“ loggen (oder Mission/Chain wartet)
  * Mode `drop`: erzeugen verhindern + audit `QUEUE_DROP`

✅ Ergebnis: euer System läuft weiter, statt RAM/DB aufzuplustern.

## Gate 2: Beim Dispatch (Inflight)

Wenn Dispatcher Jobs anstößt/bridge schreibt:

* `inflight = count_inflight_jobs()`
* wenn `inflight >= MAX_INFLIGHT`:

  * **keine neuen leases**
  * nur `INFLIGHT_SATURATED` metric + optional audit (rate-limited)
  * sleep/backoff

✅ Ergebnis: keine Dispatch-Stürme.

---

# B1.5 WebRelayBridge Integration (Push)

Ihr schreibt Jobs nach `webrelay_out`.

**Enforcement-Punkt:**

* **nur leased jobs** werden in `webrelay_out` geschrieben.
* wenn saturated: nichts schreiben (defer).

So ist eure Bridge automatisch geschützt.

---

# B1.6 Observability (Metrics + Audit)

**Modify:** euer Metrics-Modul / `record_module_call`

### Metrics (minimal)

* `queue_depth`
* `inflight`
* `drops_1m`
* `inflight_saturated_1m`
* `reaped_leases_1m`
* `retry_scheduled_1m`

### Audit Events (in euer JSONL)

* `BACKPRESSURE_QUEUE_LIMIT`
* `BACKPRESSURE_INFLIGHT_SATURATED`
* `LEASE_REAP`
* `RETRY_SCHEDULED`
* `RETRY_EXHAUSTED`

**Wichtig:** Audit event rate-limiten (z. B. max 1 pro 10s pro event-type), sonst spam.

---

# Verification Skeleton (B1)

## `verify_b1_backpressure.ps1` (Tests)

**T1 Queue Limit**

* set `MAX_QUEUE_DEPTH=5`
* spam 20 job creates
* Erwartung:

  * queue_depth bleibt bei ~5
  * drops_1m oder defer counter steigt

**T2 Inflight Saturation**

* set `MAX_INFLIGHT=2`
* starte dispatcher
* Erwartung:

  * inflight bleibt <=2
  * inflight_saturated_1m steigt

**T3 Lease Reaper**

* set `LEASE_TIMEOUT=2s`
* lease jobs, dann warte >2s
* Erwartung:

  * reaped_leases_1m steigt
  * jobs sind wieder pending/ready

**T4 Retry Budget**

* force worker failure (simulate)
* Erwartung:

  * attempts++,
  * next_retry_utc gesetzt,
  * nach max attempts → failed + RETRY_EXHAUSTED

---

## Entscheidungspunkt (damit wir nicht “zu groß” werden)

Bevor du patchst, sag mir nur **eins**:

**Habt ihr bereits eine DB-basierte Job-Tabelle mit `status`/`attempts` o. ä.?**

* Wenn **ja** → wir machen **nur migrations + lease logic**.
* Wenn **nein** → ich skizziere dir eine **kleinste JobQueue Tabelle** (2–3 Queries), die den Dispatcher sofort stabil macht.

(Keine Sorge: keine endlosen Rückfragen – nur dieses eine, weil es bestimmt, *wo* wir die Gates sauber einhängen.)
