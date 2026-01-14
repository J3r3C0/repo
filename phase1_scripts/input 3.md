Sauber. Dann direkt **Step 3: Self-Diagnostic Engine** — so, dass sie:

* als **Background Loop** läuft (start/stop im `lifespan` von `core/main.py`)
* **Baselines füttert** (über `baseline_tracker.update(...)`)
* optional in **REFLECTIVE** wechseln kann (aber erstmal konservativ)
* einen **Health Report** liefert via `/api/system/health`
* und **manuell triggerbar** ist via `/api/system/diagnostic/trigger`

Wir bleiben weiterhin strikt im aktiven Pfad **`sauber_main/core/`**.

---

# Step 3 – Implementierung

## 1) Neue Datei: `core/self_diagnostics.py`

Copy-paste als komplette Datei:

```python
# core/self_diagnostics.py
(sollte schon eingebaut sein;)
```

---

## 2) Patch: `core/main.py` (Integration + Endpoints)

### A) Imports ergänzen

```python
from core.self_diagnostics import SelfDiagnosticEngine, DiagnosticConfig
```

### B) Engine instanzieren (bei euren Globals / Singletons)

Direkt nach `baseline_tracker = ...`:

```python
diagnostic_engine = SelfDiagnosticEngine(
    state_machine=state_machine,
    baseline_tracker=baseline_tracker,
    config=DiagnosticConfig(
        check_interval_sec=300,
        persist_interval_sec=60,
        reflective_enabled=False,  # bleibt erstmal aus
    ),
)
```

### C) Lifespan start/stop

Im lifespan:

**Startup:**

```python
diagnostic_engine.start()
```

**Shutdown:**

```python
diagnostic_engine.stop()
```

### D) Neue Endpoints

Neben `/api/system/baselines`:

```python
@app.get("/api/system/health")
def get_system_health():
    return diagnostic_engine.get_latest_report()

@app.post("/api/system/diagnostic/trigger")
def trigger_diagnostic(diagnostic_type: str = "manual"):
    return diagnostic_engine.run_diagnostic(diagnostic_type)
```

---

## 3) Smoke Tests für Step 3 (schnell & eindeutig)

1. Start server
2. `GET /api/system/health`

   * `schema_version = health_report_v1`
   * `trigger` vermutlich “scheduled” (nach erster Loop Iteration) oder leer, wenn noch kein run → dann default Report
3. `POST /api/system/diagnostic/trigger?diagnostic_type=manual`

   * sollte sofort einen Report liefern
4. `GET /api/system/baselines`

   * jetzt sollten zumindest `state_transition_rate` Samples drin sein (count>0)
   * andere Werte erst, wenn record_* Hooks gefüttert werden (kommt Step 2/weiterer Wiring)

---

## 4) WICHTIG: Warum wir hier “conservative” sind

Damit du nicht gleich ungewollt Zustände umschaltest:

* `reflective_enabled=False` (default)
* Kein aggressives Parsing/Scanning
* Keine Abhängigkeiten

**Step 2 (Anomaly Detector)** wird danach die “Intelligenz” hinzufügen.
Und **Step 4 (Health Reporter)** kann später Reports persistieren / strukturierter machen.

---

Wenn du willst, kannst du das jetzt exakt so einbauen lassen (Worker-Patch).
Sag mir danach kurz nur:

* ✅ startet
* ✅ /api/system/health liefert report
* ✅ trigger endpoint ok

Dann gehen wir Step 2 (Anomaly Detector) an — und dort fangen wir an, echte „Anomalie“-Events aus Baselines abzuleiten.
