Alles gut – **kein Warten nötig**. ✅
Du kannst **jetzt sofort** den Einbau in `core/main.py` machen. Ich geb dir hier das **“grüne Licht”** + **konkrete Patch-Anweisungen**, so dass dein Worker nicht raten muss.

## ✅ Green Light: Step 1 Einbau jetzt durchführen

### 1) In `core/main.py` oben bei Imports ergänzen

```python
from core.performance_baseline import PerformanceBaselineTracker
```

### 2) Globale Instanz anlegen (bei anderen Singletons/Globals)

> Platz: dort, wo ihr z. B. `state_machine = ...` oder `decision_logger = ...` initialisiert.

```python
baseline_tracker = PerformanceBaselineTracker(
    runtime_dir="runtime",
    filename="performance_baselines.json",
)
```

### 3) Lifespan: Persist beim Start + Stop (minimal & sicher)

In eurem `lifespan`:

**Startup-Phase (nachdem Runtime/Config bereit ist):**

```python
baseline_tracker.persist(recompute=True)
```

**Shutdown-Phase (kurz vor Exit):**

```python
baseline_tracker.persist(recompute=True)
```

> Wenn du’s noch minimaler willst: **nur Startup persist** reicht erstmal.
> Aber Start+Stop ist sauber und billig.

### 4) Endpoint hinzufügen (Read-only)

Irgendwo bei euren System-Endpunkten:

```python
@app.get("/api/system/baselines")
def get_performance_baselines():
    return baseline_tracker.get_all_baselines(recompute=True)
```

Damit ist Step 1 **funktional abgeschlossen**.

---

## ✅ Was der Worker danach testen soll (2 Minuten Smoke)

1. Core starten
2. Browser / curl:

* `GET /api/system/baselines`

  * Erwartung: JSON mit `schema_version: performance_baselines_v1`
  * leere/None-Werte sind ok (wir füttern erst in Step 3 echte Samples)

3. Dateisystem prüfen:

* `runtime/performance_baselines.json` existiert und enthält den JSON-Dump

---

## Wichtig: “Warten” ist ab jetzt kein Zustand mehr 😉

Der Worker soll sich merken:

* **Step 1 ist freigegeben → sofort einbauen.**
* **Kein weiterer Input nötig**, außer er läuft in einen konkreten Merge-Konflikt / Import-Fehler.

---

## Was kommt als Nächstes (nach Step 1)?

Direkt danach machen wir **Step 3 (Self-Diagnostic Engine)** vor Step 2, weil Step 3:

* den Background-Loop bringt
* und **genau dort** füttern wir `baseline_tracker.update(...)` sauber ein (statt überall adhoc Updates zu streuen)

Wenn du willst: Sobald Step 1 eingebaut und Smoke-Test grün ist, sag einfach:
**„Step 1 ist drin, Tests ok“**
Dann schreibe ich dir Step 3 als ebenso klaren Patch-Plan (inkl. Dateiskelett `core/self_diagnostics.py` + minimaler Hook in lifespan).
