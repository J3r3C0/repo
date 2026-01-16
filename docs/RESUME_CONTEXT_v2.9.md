# Sheratan Resume Context v2.9
## Current State of Implementation

**Status**: Track B1 (Robustness) Completed. Ready for B2 (Idempotency).
**Core Core Version**: v2.9.0

### Completed Tracks (A & B1)
1. **A2: Attestation**: Heartbeat signals (build_id, capabilities) are tracked. Core in `core/attestation.py`.
2. **A3: Policy Engine**: Stateless evaluation (`core/policy_engine.py`) and persistent enforcement (`hosts` table: `policy_state`, `policy_until_utc`).
3. **A4: Node Identity**: Cryptographic Ed25519 signing for heartbeats. TOFU pinning of public keys in `hosts.public_key`. Handles `KEY_MISMATCH` and `INVALID_SIGNATURE`.
4. **B1: Backpressure & Retries**:
   - **Queue Limits**: `SHERATAN_MAX_QUEUE_DEPTH` (default 1000) blocks new jobs with 429.
   - **Inflight Limits**: `SHERATAN_MAX_INFLIGHT` (default 100) defers dispatch.
   - **Leasing**: Job status `working` requires a lease (`lease_owner`, `lease_until_utc`).
   - **Retries**: Standardized exponential backoff via `next_retry_utc` and `retry_count`.

### Key Data Structures & Files
- **Database (`core/database.py`)**:
  - `jobs`: Extended with `lease_owner`, `lease_until_utc`, `next_retry_utc`.
  - `hosts`: Extended with `policy_*`, `public_key`, `key_first_seen_utc`.
- **Dispatcher (`core/main.py`)**:
  - `_dispatch_step`: Implements Inflight Gate and Lease Reaping.
  - `_sync_step`: Implements Retry Policy and Backoff.
- **API (`core/main.py`)**:
  - `create_job_for_task`: Implements Queue Depth Gate.
  - `/api/system/metrics`: Hardware + Robustness (queue/inflight) + Legacy Compat.

### Important Notes for Continuation
- **Time Handling**: Always use `datetime.now(timezone.utc)` for ISO generation. Core avoids manual "Z" concatenation where possible to prevent double-timezone bugs.
- **Identity Mode**: Currently in **Soft-Mode** (alerts only, no block).
- **Backward Compatibility**: Dashboard relies on `queueLength` and `errorRate` in metrics.

### Next Steps (Track B2: Idempotency)
- Implement Job deduplication based on `idempotency_key`.
- Handle double-submit at the API level (G7 gate).
- Ensure Worker-side result deduplication.

---
**Resume Command**: 
"Bitte setze die Arbeit an Track B2 (Idempotency) fort, basierend auf dem Stand in `docs/resume_context_v2.9.md`."
