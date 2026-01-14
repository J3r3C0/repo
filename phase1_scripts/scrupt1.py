Perfekt. Wir machen **Step 1: Performance Baseline Tracker** — **minimal**, **robust**, **ohne neue Dependencies**, und **klar im aktiven Pfad `sauber_main/core/`**.

## Ziel von Step 1 (was danach “steht”)

* Datei **`core/performance_baseline.py`** existiert und ist lauffähig
* Rolling-Window Berechnung für **1h / 24h / 7d**
* JSON-Persistenz nach **`runtime/performance_baselines.json`**
* API-Readout (optional aber praktisch): **`GET /api/system/baselines`**
* Update-Feeding kommt erst in Step 3/2 (Self-Diagnostics/Anomaly), aber wir bauen schon die Schnittstelle.

---

# 1) Neue Datei: `core/performance_baseline.py`

> Copy-paste als komplette Datei.

```python
# core/performance_baseline.py
habe ich schon umgesetzt
```

---

# 2) Minimaler Hook in `core/main.py` (damit du’s sofort sehen kannst)

Du willst, dass dein Worker **nicht in `mesh/core`** landet — also: **nur `core/main.py` anfassen**.

### A) Import + globale Instanz (oben bei Imports/Globals)

```python
from core.performance_baseline import PerformanceBaselineTracker

baseline_tracker = PerformanceBaselineTracker(
    runtime_dir="runtime",
    filename="performance_baselines.json",
)
```

### B) Lifespan: einmalig persistieren bei Start/Stop (optional aber gut)

Im lifespan (Startup/Shutdown Bereich):

```python
# on startup (nach init)
baseline_tracker.persist(recompute=True)

# on shutdown (vor exit)
baseline_tracker.persist(recompute=True)
```

### C) Endpoint (Read-only)

```python
@app.get("/api/system/baselines")
def get_performance_baselines():
    return baseline_tracker.get_all_baselines(recompute=True)
```

> Wichtig: **Update-Feeding** (tracker.update(...)) kommt als nächstes über Step 3 (Self-Diagnostics Engine) oder Step 2 (Anomaly), damit wir nicht “random metrics” irgendwo reinpatchen.

---

## 3) Was du nach Step 1 sofort testen kannst

1. Server starten
2. `GET /api/system/baselines` → du siehst die Struktur + leere/None Werte
3. Du findest im Dateisystem: `runtime/performance_baselines.json`

---

## 4) Kurz: Wo füttern wir später echte Werte ein?

Damit der Worker “richtig” füttert:

* **Job Success Rate**: aus Worker Results / Job outcomes
* **Avg Latency**: aus Job start/end timestamps
* **State Transition Rate**: aus state_machine transition logs
* **LLM Call Success Rate**: aus WebRelay client responses
* **Worker Availability**: aus Heartbeats/health endpoints

Das machen wir sauber in **Step 3**, sobald `SelfDiagnosticEngine` den Background-Loop hat.

---

Wenn du willst, sag mir kurz:

* Läuft dein aktiver Serverstart wirklich über `core/main.py` (FastAPI app dort)?
  Dann bleiben wir exakt auf diesem Pfad und machen als nächstes **Step 2 oder Step 3** (ich empfehle **Step 3 Self-Diagnostics Engine**, weil sie das Feeding + Persist automatisch orchestriert).
