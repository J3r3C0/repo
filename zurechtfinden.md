eine **grobe, aber effektive “Worker-sichere” System-Übersicht**, damit ein Worker-Modell **nicht in der falschen Core-Struktur** landet und Phase-1/Phase-D (Reflexive Capabilities) sauber andocken kann.

---

## 0) Ziel dieser Übersicht

**Problem:** Es gibt mehrere “Core”-ähnliche Strukturen (z. B. `core/` und `mesh/core/`).
**Ziel:** Dein Worker soll wissen:

1. **Welche Pfade sind “Source of Truth” (SoT)**
2. **Welche Pfade sind “Legacy/Migration Mirror”**
3. **Wo Phase-1 (Baseline Tracker) + Phase-D (Self-Diagnostics/Anomalies/Health Reports) integriert werden** 

---

## 1) “Source of Truth” (Active Code Path) – NUR HIER arbeiten

### ✅ Primär (aktiv / aktuell maßgeblich)

**`sauber_main/core/`**
Hier sitzt das **laufende System**, an das Phase-1 und die kommenden Reflexionsmodule andocken sollen.

**Wichtige Dateien (Phase 1 + Phase D relevant):**

* `core/main.py`

  * FastAPI App, Lifespan/Startup/Shutdown
  * Hier wird der **Background-Loop** für Diagnostics/Baselines gestartet (laut Plan) 
* `core/state_machine.py`

  * Zustände + Transitions + Logging
  * Hier kommt später die **“unexpected transition → trigger diagnostic”** Hook rein 
* `core/decision_trace.py` (+ `core/why_api.py`, `core/why_reader.py` falls vorhanden)

  * bestehendes “Warum/Trace” System (Basis für Reflexion/Reports) 

### ✅ Runtime Daten (wo die Reflexion persistent werden soll)

**`sauber_main/runtime/`** (oder äquivalente Runtime-Zone im Projekt)

* `runtime/performance_baselines.json` (laut Plan) 
* ggf. `runtime/health_reports.jsonl` / `runtime/anomalies.jsonl` (würde ich empfehlen, siehe unten)

---

## 2) Migration / Mirror / Legacy – HIER NICHT IMPLEMENTIEREN (vorerst)

### ⚠️ “Parallelstruktur” (sieht echt aus, ist aber nicht das Ziel für Phase 1)

**`sauber_main/mesh/`** (insb. `mesh/core/…`)

* Das ist sehr wahrscheinlich ein **Migrations-/Mirror-Tree**, der irgendwann die alte Struktur ablösen soll.
* Für **jetzt** (Phase 1 + Reflexive Capabilities) gilt:

  * **Nicht dort bauen**
  * Nicht dort “fixen”
  * Nicht dort “Hooks einbauen”

**Worker-Regel:**

> Wenn ein File in `mesh/core/` existiert und es gibt ein analoges File in `core/`, dann ist **`core/` der aktive Pfad**. Alles Reflexive geht zuerst in `core/`.

Das passt auch zur Abweichungsmatrix: Phase D soll auf dem existierenden State Machine / Decision Trace aufsetzen, nicht parallel woanders. 

---

## 3) Phase-1/Phase-D Module: Wo kommen die neuen Dateien hin?

Aus dem Plan ergeben sich vier neue Module. **Alle nach `sauber_main/core/`**: 

### Step 1 (Phase 1 Foundation)

* `core/performance_baseline.py`

  * Rolling Windows + JSON Persistence
  * Storage: `runtime/performance_baselines.json` 

### Step 2

* `core/anomaly_detector.py`

  * Baseline deviation + heuristics

### Step 3

* `core/self_diagnostics.py`

  * Background loop + “enter_reflective_mode()” Logik

### Step 4

* `core/health_reporter.py`

  * Report format, health_score, findings, recommendations

---

## 4) Integration Points (damit der Worker nicht “irgendwo” andockt)

### A) `core/main.py` (einziger Startpunkt)

Hier rein:

* Instanziieren von:

  * `PerformanceBaselineTracker`
  * `AnomalyDetector`
  * `SelfDiagnosticEngine`
  * optional `HealthReporter` (oder Reporter als Teil der Engine)
* Lifespan:

  * `diagnostic_engine.start()`
  * `diagnostic_engine.stop()` 
* Neue Endpoints:

  * `/api/system/health`
  * `/api/system/baselines`
  * `/api/system/anomalies`
  * `/api/system/diagnostic/trigger` 

### B) `core/state_machine.py` (Hook für “unexpected transitions”)

Hier rein:

* `if _is_unexpected_transition(...): trigger diagnostic(...)` 

### C) Runtime Persistence (einheitlich!)

Empfehlung (sehr worker-freundlich):

* Baselines: `runtime/performance_baselines.json`
* Reports: `runtime/health_reports.jsonl`
* Anomalies: `runtime/anomalies.jsonl`

So kann jedes Modul append-safe sein und du hast ein klares Audit-Trail-Format.

---

