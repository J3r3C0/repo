**vollständigen Bauplan** mit **Gates, DoD, Nicht-Zielen, Guardrails und state_hash**.

> **Einfügen ab hier** (am besten als neue Sektion „Bauplan / Execution Gates“):

---

## Bauplan: Execution Gates, DoD, Guardrails (Core-Zielzustand)

### Zielzustand (Core in Finalform)

Der **Core ist ein deterministischer Perception-Kernel**. Er nimmt Events entgegen und gibt ausschließlich **States/Identity-Candidates** aus.

**Core darf nur:**

* `Event -> EventBuffer -> Resonance -> MemoryUpdate -> IdentityRanking`
* read-only Snapshots: `/api/state`, `/api/identity`, optional `/api/identity/{segment_id}`
* deterministisches Replay: `/api/replay`

**Core darf NICHT (Nicht-Ziele / harte Verbote):**

* keine Mission/Task/Job-Orchestrierung
* kein Dispatching / Scheduling / Queue-Ownership
* keine Policy-/Governance-Enforcement-Entscheidungen (nur Bewertung/Scoring, falls überhaupt)
* keine MCTS/Planning/Action-Selection
* keine Netzwerktopologien (Mesh), keine UI, kein WebRelay-Routing
* keine Zeit-/Random-abhängige Logik im Core (kein `time.time()`, kein `random`, keine globale Mutationen außerhalb Memory)

**Schichtung (unidirektional):**

* `hub/` importiert `core/`
* `core/` importiert **niemals** `hub/`

---

## Determinismus: Canonical `state_hash`

### Zweck

`state_hash` ist die binäre Wahrheit: gleiche Inputs + gleiche Config => gleicher Hash.

### Definition (DoD)

* `state_hash = sha256( canonical_bytes(memory) + canonical_bytes(identity_snapshot) + cycle_count + config_fingerprint )`
* `config_fingerprint` enthält mind.:

  * `WINDOW_SIZE`, `WINDOW_OVERLAP`, `CHANNELS`
  * `MAX_ACTIVE_STATES`, `MAX_AGE`
  * `THRESHOLDS` (per Channel)
  * GPU flags (on/off), dtype, device id (nur als String; darf Ergebnis nicht nondeterministisch machen)

### DoD für Determinismus

* `determinism_test` erzeugt über **N=20 Runs** identischen `state_hash`
* `replay_test` (log → replay) ergibt exakt denselben `state_hash` wie Live-Run

---

## Gate-Plan (Sequenz mit Stop-Lines)

### Gate A — Core Purity + Baseline (blockiert alles weitere)

**Implementieren**

* `tools/verify_phase1.py` erweitern:

  * Fail wenn in `core/` Keywords vorkommen: `mcts`, `dispatch`, `recommend_action`, `mission`, `task`, `job`, `policy_enforce`, `orchestrator`
  * Fail wenn `core/` `hub/` importiert
  * Fail wenn `core/` `time`, `random` nutzt (außer deterministische Stubs/clock injection, falls explizit vorgesehen)
* `state_hash` implementieren (siehe oben)

**DoD**

* `python -m tools.verify_phase1` => PASS
* `python -m tests.determinism_test` => PASS (N=20)
* `python -m tests.gpu_smoke_test` => PASS (wenn GPU enabled)

**Stop-Line**

* Gate A muss 100% grün sein, bevor Gate B startet.

---

### Gate B — Identity v3 (Thresholds + Persistenz + Top-K)

**Implementieren**

* `IdentityRanking` deterministisch:

  * Filter pro Channel über `threshold[channel]`
  * Persistenzregel: Segment darf unter Threshold bleiben, wenn `last_seen <= max_age` UND `weight/persistence_factor` noch > minimal
  * Ranking deterministisch: primary `score`, secondary `last_seen` (neuere zuerst), tertiary `segment_id` (als tie-breaker)
* Hard limit: `MAX_ACTIVE_STATES` (Memory + Identity dürfen nicht darüber wachsen)

**DoD**

* `identity_rank_test`:

  * gleiche Inputs => gleiche Rangfolge
  * tie-breaker greift korrekt
* `persistence_test`:

  * Segment fällt unter Threshold, bleibt aber innerhalb `max_age` erhalten
* Speichergrenze:

  * `MAX_ACTIVE_STATES` wird niemals überschritten (auch bei Stress)

**Stop-Line**

* Erst wenn Gate B Tests grün sind → Gate C.

---

### Gate C — Rolling Windows (Phase-3 Zeitfenster)

**Implementieren**

* Events mappen deterministisch auf `window` + `segment_id`:

  * `window_id = floor(t / WINDOW_SIZE)` (oder event_index-basiert, falls ohne Zeit)
  * `WINDOW_OVERLAP` deterministisch: ein Event kann in exakt `k` Windows liegen (definiert durch Config)
* Memory update pro (channel, window) segmentiert, keine „hidden“ Zeitquellen.

**DoD**

* `rolling_window_test`:

  * exakt definierte Zuordnung (k windows)
  * Resonanzsummen reproduzierbar
* `determinism_test` bleibt PASS

**Stop-Line**

* Kein API-Umbau / Replay-Finalisierung bevor Rolling-Windows stabil.

---

### Gate D — Replay & API Stabilisierung (Core-Adapter-API final)

**Implementieren**

* Endpunkte final (Core):

  * `POST /api/event` (ingest)
  * `GET /api/state` (snapshot)
  * `GET /api/identity` (Top-K / ranking)
  * optional `GET /api/identity/{segment_id}`
  * `POST /api/replay` (log replay)
* Jede Antwort enthält:

  * `cycle_count`, `state_hash`, `config_fingerprint`
* Replay nutzt ausschließlich Log-Events, keine Live-Nebenquellen.

**DoD**

* `api_contract_test`:

  * Response schema stabil (inkl. state_hash)
* `replay_test`:

  * replay == live (state_hash equal)

**Stop-Line**

* Keine Hub/Mesh-Integration bevor API stabil.

---

### Gate E — GPU Primitives (Deterministische Performance-Schicht)

**Implementieren**

* GPU berechnet nur rohe Resonanzwerte (Segment-Reduce / Prefix-Scan / Aggregation)
* CPU macht Threshold/Ranking/Persistenz (Bedeutungszuweisung)
* deterministische dtype/ordering fixieren (z.B. stable sort/tie-breaker auf CPU)

**DoD**

* `gpu_determinism_test`:

  * GPU enabled/disabled: **identischer state_hash** (oder exakt dokumentierte Abweichung, dann als “not supported” definieren)
* Performance check dokumentiert (Events/sec, VRAM)

**Stop-Line**

* Wenn GPU nicht deterministisch: GPU-Mode als optional deklarieren; Core-DoD bleibt CPU-deterministisch.

---

## Integrationsregel (Hub/Mesh)

**Erst nach Gate D** darf Hub/Mesh den Core konsumieren.

Hub darf:

* Jobs, Missions, Worker, WebRelay, Dispatch
* UI, Mesh, Broker, Registry
* Policies/Controls/Rate-Limit

Core darf:

* nur Events/State/Identity/Replay

---

## Release-Checklist (Final Core)

* [ ] verify_phase1 PASS
* [ ] determinism_test PASS (N=20)
* [ ] identity_rank_test PASS
* [ ] persistence_test PASS
* [ ] rolling_window_test PASS
* [ ] replay_test PASS
* [ ] api_contract_test PASS
* [ ] (optional) gpu_determinism_test PASS
* [ ] README: Core Scope & Nicht-Ziele klar beschrieben
* [ ] Changelog: Gate A–E abgeschlossen, commit refs

---

**Ende Patch**

---

