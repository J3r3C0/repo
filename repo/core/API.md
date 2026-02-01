# Sheratan Core: API & Determinism Specification

## 1. Core Principles

### Determinism (`state_hash`)
The Sheratan Core is a state-machine that processes events into resonance. Every cycle produces a unique `state_hash` computed as:
`SHA256(SortedBytes(SegmentStates))`

This hash is the ultimate proof of correctness. Two identical event streams must produce identical hashes.

### Purity (Import Guard)
`core/` logic never imports from `hub/`, `mesh/`, or `ui/`. 
The purity is enforced by `tools/verify_phase1.py`.

---

## 2. API Endpoints (Port 8001)

### `GET /api/state`
Returns a full snapshot of active resonance segments.
- **Includes**: `state_hash`, `cycle_count`.
- **Fields**: `segment`, `value`, `weight`, `decay`, `last_seen`.

### `GET /api/identity`
Returns the "Identity Layer" (Top-K selection).
- **Parameters**: `threshold` (default 0.5), `top_k` (default 10).
- **Logic**: Uses **Adaptive Thresholding** and **Persistence (Hysteresis)**.

### `GET /api/identity/{segment_id}`
Deep lookup for a specific segment's resonance state.

### `POST /api/event`
Ingest raw events into the buffer.
- **Format**: `{"events": [(id, value, timestamp, channel), ...]}`

### `POST /api/replay`
Reconstructs state from a historical CSV log.
- **Format**: `{"log_path": "logs/resonance_log.csv"}`
- **Return**: Resulting `state_hash`.

---

## 3. Identity v3 Logic

The selection process follows these rules:
1. **Adaptive Threshold**: If system load (segment count) is high, the base threshold is raised automatically.
2. **Persistence**: If a segment was in the previous Top-K, it is kept even if it falls slightly below threshold (Hysteresis window = 5 cycles).
3. **Aging**: Ranking score = `value * (1.0 - age * 0.01)`.

---

## 4. Replay Mechanism

Replay bypasses the FastAPI ingestion and reads directly from `CSV`. It uses the same `SheratanEngine` logic to ensure that historical analysis matches live perception bit-by-bit.
