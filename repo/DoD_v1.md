Ja – und **jetzt ist genau der richtige Zeitpunkt**, eine **harte, schriftliche Definition of Done (DoD)** zu setzen.
Nicht technisch offen, nicht visionär, sondern **abschließend, drift-resistent, prüfbar**.

Ich mache das in drei Ebenen:

1. **Primäre DoD – “Sheratan Evolution v1 = DONE”**
2. **Explizite Nicht-Ziele (Anti-Drift-Schutz)**
3. **Change-Regeln nach DONE (Governance light)**

So bleibt der Zustand stabil, ohne Entwicklung zu blockieren.

---

# 1) Definition of Done

## *Sheratan Evolution v1 – Abgabefähig*

Sheratan Evolution v1 gilt als **DONE**, wenn **alle** folgenden Kriterien erfüllt und **nachweisbar** sind.

---

## A. Architektur & Struktur (objektiv prüfbar)

**A1. Repo-Struktur**

* `repo/` enthält:

  * `core/`, `plugins/`, `tools/`, `schemas/`, `requirements/`, `ui/dist/`
* Alte Implementierungen liegen **außerhalb** von `repo/` und werden **nicht** referenziert.
* `repo/` ist **allein lauffähig** (Dev & Build).

**A2. Trennung Körper / Seele**

* Körper:

  * FastAPI App
  * Runner
  * DB (SQLite + WAL)
  * UI Static Serving
* Seele:

  * Schemas (decision_trace)
  * Policy / Routing
  * Trace-Semantik
* Keine Policy-Logik in Build-/Packaging-Code.
* Keine Build-Annahmen in Core-Logik.

➡️ **DoD-Check:** Architekturdiagramm lässt sich ohne Widersprüche zeichnen.

---

## B. Safety Net (nicht verhandelbar)

**B1. SystemExercise**

* `repo/tools/system_exercise.py` existiert und:

  * startet den Core selbst (Subprocess)
  * nutzt freien Port
  * isoliert `SHERATAN_DATA_DIR`
  * wartet aktiv auf `/api/system/health`
  * testet:

    * health
    * DB/WAL
    * read_file
    * write_file (temp)
    * walk_tree (bounded)
    * decision_trace geschrieben & nicht leer
    * UI `index.html` erreichbar
* erzeugt:

  * `build/reports/exercise_report.json`
  * `build/reports/feature_matrix.json`

**B2. Gate-Regel**

* **Kein Shrink-Schritt** (Excludes, Lazy Imports, Feature Packs)
  ohne **grünen Exercise-Run**.

➡️ **DoD-Check:** `python tools/system_exercise.py` → PASS.

---

## C. Conservative Shrink vollständig materialisiert

**C1. Dependency-Trennung**

* `requirements/core.txt`
* `requirements/extras.txt`
* `requirements/dev.txt`
* Core läuft **ohne** Extras.

**C2. PyInstaller**

* `onedir`
* konservative `excludes`
* UI nur als `ui/dist`
* keine Dev-Deps im Release

**C3. Lazy Loading**

* Plugin-Ausführung nutzt `importlib`
* Keine schweren Imports im App-Startpfad

➡️ **DoD-Check:** Cold-Start funktioniert ohne Extras.

---

## D. Messinstrumente aktiv (Beobachten ≠ Entfernen)

**D1. Import-Trace**

* `tools/import_trace.py` vorhanden
* Aktivierbar via `SHERATAN_IMPORT_TRACE=1`
* Schreibt `build/reports/imports_used.txt`
* **Read-only** (keine automatische Ableitung)

**D2. Size-Report**

* `tools/size_report.py` vorhanden
* Schreibt `build/reports/size_report.json`
* Zeigt:

  * Gesamtgröße
  * File-Count
  * Top-Bloat-Files

➡️ **DoD-Check:** Beide Reports entstehen im CI oder lokal.

---

## E. Produktreife (minimal, aber real)

**E1. Build**

* PyInstaller-Build erzeugbar
* Build startet
* Exercise läuft gegen Build (nicht nur Dev-Run)

**E2. Fallback**

* Alte Welt existiert weiterhin **außerhalb** von `repo/`
* Keine Verflechtung
* Rückfall möglich, aber nicht Teil von v1

➡️ **DoD-Check:** Build + Exercise = PASS.

---

## F. Dokumentierter Endzustand

Mindestens folgende Aussagen sind **wahr** und **dokumentiert**:

* „Sheratan Evolution v1 ist ein **modularer, messbarer, shrink-barer Core**“
* „Funktionalität wird **nie** durch Abspecken verloren, sondern nur durch bewusste Feature-Packs deaktiviert“
* „SystemExercise ist das letzte Wort über Nutzbarkeit“

➡️ **DoD-Check:** README/struktur.md widersprechen dem Code nicht.

---

# 2) Explizite Nicht-Ziele (Anti-Drift-Block)

Diese Dinge sind **bewusst NICHT Teil von v1**:

❌ Autonomes Lernen
❌ Selbst-Rewrite-Loops
❌ Feature-Pack-Distribution
❌ Nuitka / aggressive Compilation
❌ Automatisches Excluding basierend auf Import-Trace
❌ Performance-Optimierung jenseits Stabilität
❌ “Seele erweitern” (neue Policy-Dimensionen)

> **Regel:** Wenn etwas nicht explizit in der DoD steht, ist es **nicht erlaubt**, es stillschweigend einzubauen.

---

# 3) Governance nach DONE (drift-resistent)

Ab dem Moment, wo du sagst **“DONE”**, gilt:

### G1. Versionsregel

* Alles danach ist **v1.x** oder **v2**
* v1 selbst wird **nicht mehr semantisch verändert**

### G2. Änderungsregel

Eine Änderung **nach DONE** braucht mindestens:

1. neue DoD-Erweiterung **oder**
2. neue Phase (z. B. *Evolution v2*)

### G3. Safe-Question (entscheidend)

Bei jeder neuen Idee darfst du nur eine Frage stellen:

> **„Verändert das den Zielzustand von v1 – oder nur den Weg dorthin?“**

* Zielzustand verändert → **nicht erlaubt**
* Weg verändert → **erlaubt**, aber nur mit grünem Exercise

---

## Klartext

Du bist **nicht 0 Meter davor** –
du bist **drüber**.

Was dir jetzt fehlt, ist **kein Code**, sondern **ein offiziell erklärter Endzustand**.
Diese DoD ist genau dafür gedacht.

Wenn du willst, formuliere ich dir im nächsten Schritt:

* eine **1-seitige „Sheratan Evolution v1 – DONE Erklärung“** (Commit-Message-fähig)
* oder eine **Phase-Lock-Policy** (kurz, maschinenlesbar, z. B. YAML/JSON).
