# Spec → Job Ownership & Lease Policy

## Goal
Define a single source of truth for materialising jobs from chain specifications and a clear lease/ownership model that works safely with multiple ChainRunner instances.

## Entities (DB tables)
- **chain_spec** – description of the work to be performed.
- **job** – concrete unit of work derived from a spec.
- **dispatch_lease** – temporary claim on a job for the Dispatcher.
- **spec_lease** – temporary claim on a spec for the ChainRunner.

## Ownership Rules
| Actor | Responsibility | Lease Type |
|-------|----------------|------------|
| **ChainRunner** | Materialises a `job` from a `chain_spec`. | `spec_lease` (TTL, owner_id) |
| **Dispatcher** | Dispatches a `job` to the WebRelay bridge. | `job_lease` (TTL, owner_id) |

## Lease Mechanics
- Leases are stored in the DB with a **TTL** (e.g., 60 s). The owner must refresh the lease before expiry.
- If a lease expires, another instance may acquire it.

## Idempotent Job Creation
- A deterministic **step_key** identifies the work step (e.g. `root`, `step:2:call_llm`).
- **Unique constraint** on `(spec_id, step_key)` guarantees at most one job per step.
- `INSERT … ON CONFLICT DO NOTHING` (or upsert) is used; a conflict means the job already exists – safe to continue.

## Flow
1. **ChainRunner** polls `chain_spec` with status `pending`.
2. Attempts to acquire a `spec_lease` (INSERT with owner_id, expires_at).
3. On success, materialises jobs:
   ```sql
   INSERT INTO job (spec_id, step_key, status, ...) 
   VALUES (...)
   ON CONFLICT (spec_id, step_key) DO UPDATE SET status='pending';
   ```
4. Marks the spec as `materialized` (or `in_progress`).
5. **Dispatcher** polls `job` with status `pending` and acquires a `job_lease`.
6. Writes the job file to `runtime/narrative` and updates `job.status='dispatched'`.

## Retry & Recovery
- **Spec lease expiry** → another ChainRunner can pick up the spec.
- **Job insert conflict** → job already exists, continue.
- **Job lease expiry** → Dispatcher will retry later.

---
> **Decision**: ChainRunner owns spec‑to‑job materialisation; Dispatcher only dispatches jobs. This eliminates duplicate job creation and keeps the Dispatcher simple.
