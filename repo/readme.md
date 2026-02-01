<<<<<<< HEAD
# Sheratan Repo (Deprecated)

⚠️ **Status:** Deprecated / nicht mehr aktiv.

Dieses Repository ist eine ältere Sammel-/Meta-Repo-Variante und wird nicht weiter gepflegt.
=======
# Sheratan Core: Perception-Kernel

**Deterministic, Segment-Based Perception Engine**

[![Target State](https://img.shields.io/badge/Sheratan-Perception%20Kernel-blueviolet)](https://github.com/J3r3C0/sheratan-core)
[![Status](https://img.shields.io/badge/Status-Kernel--v1%20(Candidate)-blue)](https://github.com/J3r3C0/sheratan-core)
[![Determinism](https://img.shields.io/badge/Determinism-Verified-success)](https://github.com/J3r3C0/sheratan-core)
>>>>>>> 0d05299baf01209327a7b0a1e6eb7b526f866bcb

**Nachfolger:** `sheratan-core-v2` (Source of Truth fuer den System-Kern).

<<<<<<< HEAD
Bitte verwende fuer neue Arbeiten und Referenzen ausschliesslich `sheratan-core-v2`.
=======
## The Philosophy: Perception & Salience

Sheratan Core is a specialized perception engine. Following the **Core Purity** mandate, all "Agency" (Missions, Tasks, Jobs) has been relocated to the hub, leaving the Core to focus on high-fidelity signal extraction.

- **Input**: Raw Event Streams (Channel, Value, Timestamp).
- **Processing**: Segmented Resonance computation and rolling window analysis.
- **Memory**: Deterministic state aging and decay.
- **Output**: Salience-based Identity Selection (Top-K states).

**Decision logic, mission planning, and tool execution reside exclusively in the `hub/`.**

---

## Quick Start (Kernel Mode)

```bash
# Start the Core Perception API (FastAPI)
START_CORE_ONLY.bat
```

**Accessing Perception:**
- **State Snapshot**: `GET http://localhost:8001/api/state`
- **Identity (Top-K)**: `GET http://localhost:8001/api/identity`
- **Deterministic Replay**: `POST http://localhost:8001/api/replay`

---

## Key Features

### 1. Deterministic state_hash
Every resonance cycle produces a canonical SHA256 `state_hash`. Replaying the same event stream under identical runtime constraints (single-threaded, stable float mode) produces bit-identical results.

### 2. Identity Selection (v3 Logic)
- **Hysteresis (Persistence)**: Adaptive thresholds that prevent rapid state-flipping; recently selected states remain active if they stay within a defined stability window.
- **Adaptive Thresholds**: Selection sensitivity adjusts based on segment density and system load.
- **Temporal Ranking**: Modernity and resonance intensity are weighted to prioritize current relevant signals.

### 3. Rolling Windows
Events are mapped to overlapping temporal segments, reducing boundary loss and ensuring signal continuity across segment transitions.

---

## Kernel Contracts (v1)

To ensure system reliability, the Core adheres to the following technical contracts:

- **Determinism Contract**: Given the same `evolution.lock.json` and event sequence, the resulting state hashes are invariant across supported Python environments.
- **Replay Equivalence**: Live ingestion and batch replay from storage are functionally identical for all perception metrics.
- **Purity Guard**: The Core directory is forbidden from importing any `hub/` or `agency` components, enforced by automated CI checks.

## Non-goals (v1)

- **GPU Determinism**: While GPU paths are planned for acceleration, byte-perfect determinism is currently only guaranteed on CPU-based replay.
- **Semantic Understanding**: The Core identifies *salience* and *resonance*, not linguistic "meaning" or intent.
- **Autonomous Activity**: The Core produces state snapshots; it does not "do" anything or initiate actions.

---

## Architecture: Core vs. Hub

| Feature | Core (Kernel) | Hub (Agentic) |
| :--- | :--- | :--- |
| **Primary Role** | Perception / Filtering | Control / Planning |
| **Logic Type** | Mathematical / Signal | LLM / Procedural |
| **Execution** | Deterministic Cycles | Real-time Operations |
| **Storage** | Volatile State Memory | Persistent Databases |
| **Dependencies** | Minimal / Purity-Locked | Full System Integration |

---

## Verification

Run the purity and determinism suite:
```bash
# 1. Check Purity (Ban agentic keywords in core)
python -m tools.verify_phase1

# 2. Check Determinism (Replay stress suite)
python determinism_stress_test.py

# 3. Check Boundary Coverage
python rolling_window_test.py

# 4. Check Replay Consistency
python -m pytest tests/test_replay_purity.py
```

---

## Visualization

Observe the resonance landscape and state transitions:
```bash
python tools/viz_kernel.py
```

---

## License

MIT - Sheratan Perception-Kernel


>>>>>>> 0d05299baf01209327a7b0a1e6eb7b526f866bcb
