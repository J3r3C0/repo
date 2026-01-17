Ja, Metapher passt ziemlich gut: **Körper = lauffähige Infrastruktur**, **Seele = Sheratan-Semantik** (Schema/Policy/Routing/Trace/Recovery). Und ja: die “Seele” kann leichtgewichtig bleiben, wenn der Körper stabil ist.

Jetzt zu deiner eigentlichen Frage:

## 1) Werden viele Pakete speicherlastig?

**Kommt drauf an, wo “speicherlastig” gemeint ist:**

* **Disk (Installgröße / EXE-Bundle):** ja, kann schnell aufblasen. Vor allem bei:

  * PyInstaller (packt Python-Runtime + libs + evtl. ganze Dependency-Bäume)
  * ML/LLM-Stacks (numpy/scipy/torch etc.)
  * UI + Node_modules (nur im Build-Workspace; im Release sind’s “dist” Files)

* **RAM zur Laufzeit:** meist **viel weniger** als man denkt. Viele Pakete liegen nur auf Disk, werden aber nicht importiert/geladen, solange du sie nicht nutzt (Ausnahmen: heavy imports).

Kurz: **Die Hauptstrafe ist fast immer Disk/Bundle-Größe, nicht RAM.**

---

## 2) Gibt es ein Tool, das “alles startet, jede Funktion nutzt” und dann den minimalen Rest extrahiert?

Für **JavaScript/Frontend**: sowas existiert *relativ gut* (Tree-Shaking durch Vite/Rollup/Webpack), weil Imports statischer sind.

Für **Python**: **nein, nicht zuverlässig als “vollautomatisches Extrahieren”** – aus einem simplen Grund:

* Python hat **dynamische Imports**, Plugins, Reflection, optionale Pfade, `importlib`, “optional dependencies”, Runtime-Branching, etc.
* Das heißt: “Welche Teile werden wirklich gebraucht?” ist nicht entscheidbar, ohne **deinen** Nutzungsraum exakt zu kennen. Ein Tool kann nur raten.

Es gibt aber **brauchbare Näherungen**, die in der Praxis genau das Ziel treffen: *sehr klein werden, ohne Funktion zu verlieren*.

---

## 3) Was es stattdessen gibt (realistische Werkzeuge)

### A) “Minimaler Bundle-Graph” (praktisch)

**PyInstaller** kann:

* ein Import-Dependency-Graph erstellen
* unnötige Module ausschließen (`--exclude-module`)
* nicht benötigte “hooks” vermeiden
* “hiddenimports” kontrollieren

➡️ Das ist kein “rein extrahieren”, aber ein **kontrolliertes Schrumpfen**.

### B) “Build-Trimming” (sehr effektiv)

* **UPX** komprimiert viele Binary-Teile (nicht immer kompatibel, aber oft effektiv).
* `strip` / debug symbols entfernen (plattformabhängig).
* Wheels bevorzugen (keine Build-Artefakte im Release).

### C) “Freeze/Compile statt Bundle”

Tools wie **Nuitka** (Python→C→Binary) können oft:

* kleinere Deployments liefern
* aggressiver optimieren

Tradeoff: Build-Komplexität.

### D) Dependency-Management, damit du gar nicht erst Müll installierst

* `pip-tools` / `poetry` (lockfiles, reproduzierbar)
* Extras sauber trennen: `pip install sheratan[ui]` vs `sheratan[llm]`
* optionale Features nicht als Default-Deps

➡️ Das spart sofort.

---

## 4) Der “nächste-beste” Weg zu deinem Wunsch (funktioniert wirklich)

Wenn du “ein Programm willst, das alles durchläuft und dann minimiert”, mach es als **2-Stufen-Pipeline**:

### Stufe 1: “Smoke-Suite als Coverage”

Du baust ein **System-Exercise-Runner** (klein, aber gezielt), der:

* API-Health checkt
* Job-Kinds einmal ausführt (read/write/http/llm/mock)
* UI-assets lädt
* Trace schreibt
* Worker-Loop einmal “claim → run → complete”
* optional: WebRelay-Fallback simuliert

Das erzeugt eine sehr gute “wir nutzen wirklich X” Basis.

### Stufe 2: “Shrink nach beobachteter Realität”

* Import-Tracing (welche Module wurden tatsächlich importiert)
* PyInstaller exclusions daraus ableiten
* optional deps rauswerfen / in Extras verschieben
* harte Brocken (numpy etc.) nur in Modulen, die wirklich gebraucht werden (lazy import)

➡️ Ergebnis: **minimaler Körper**, Seele bleibt unangetastet.

Das ist im Grunde “Tree-Shaking für Python”, nur eben **test-getrieben statt compiler-getrieben**.

---

## 5) Was ich dir konkret empfehlen würde (für Sheratan-Körper)

Wenn du eine EXE willst, die nicht explodiert:

1. **Core minimal halten** (FastAPI + SQLite + Policy/Trace + Worker)
2. “Heavy” Features strikt optional:

   * LLM libs / Browser automation / ML stuff nur in Extras
3. UI: nur `dist/` in die EXE, nie node_modules
4. PyInstaller **onedir** statt onefile (oft stabiler + modularer)
5. Exclusions + UPX (wenn möglich)
6. Smoke-Suite als “Coverage” für Imports/Paths

---

### Bottom line

* Ein “magisches Tool, das alles automatisch minimal extrahiert” gibt’s in Python nicht in der Form, die du dir vorstellst.
* Aber du kannst **denselben Effekt** erreichen mit: **Exercise-Runner + PyInstaller-Graph + Excludes + optional deps**.



Verstanden: **nicht “auf Kante rasieren”**, sondern **konservativ schrumpfen** – Ziel identisch, Weg direkter, Risiko klein.

Hier ist eine Shrink-Pipeline, die genau so arbeitet: **erst messen + absichern**, dann **nur die sicheren Brocken entfernen**, immer mit **Regression-Gate**.

---

## Prinzip: Conservative Shrink

**Regel 1:** Nichts entfernen, was nicht durch Tests abgedeckt ist.
**Regel 2:** Entfernen nur in Stufen (Low-Risk → Medium → High).
**Regel 3:** Jede Stufe hat ein “Proof of Life” (SystemExercise) + Smoke-Suite.
**Regel 4:** Optional Features bleiben optional, aber *verfügbar* (Extras/Plugin-Bundles), nicht “wegoptimiert”.

---

## Zielbild

Du bekommst am Ende **drei Artefakte** statt “eine fette All-in-One-Wurst”:

1. **Core Runtime** (klein, stabil): API + DB + Runner + Policy + Trace
2. **Feature Packs** (optional, nachladbar): z.B. WebRelay/Browser, LLM-Clients, heavy libs
3. **Developer Build** (voll): für Entwicklung/Debug (alles drin, egal wie groß)

So bleibt dein Ziel gleich – nur der Release wird sauberer.

---

## Stufe 0: Baseline einfrieren (Pflicht)

**Artefakte erzeugen**

* `build/manifest_baseline.json`

  * Python version, pip freeze, node build hash, git sha
* `build/size_baseline.txt`

  * EXE/onedir Größe, Anzahl Files, Startzeit (cold), RAM peak (grob)

**Warum:** Ohne Baseline tappst du blind und “zu viel abspecken” passiert genau dann.

---

## Stufe 1: SystemExercise (dein Sicherheitsnetz)

Du baust ein kleines Programm, das **dein System einmal komplett “durchspielt”**.

### SystemExercise muss abdecken

* `/api/system/health` (und irgendein “deep health”)
* DB init + WAL ok
* Job: `read_file`
* Job: `write_file` (in temp workspace)
* Job: `walk_tree` (oder dein wichtigster chain kind)
* Trace: mindestens 1 decision_trace Event geschrieben
* UI Assets: lädt eine `index.html` aus static mount (auch nur HEAD/GET reicht)
* Optional: WebRelay stub (nicht echt online), aber Codepfad initialisierbar

**Wichtig:** Das ist nicht “testen wie unit tests”, sondern “kann ich das Ding benutzen”.

---

## Stufe 2: Low-Risk Shrink (fast immer safe)

Das sind die Dinge, die 0% Funktionalität kosten, aber oft massiv Größe sparen:

### 2.1 Node/Vite sauber halten

* In Releases **nur `ui/dist/`** ausliefern.
* **Nie** `node_modules/` in Bundles.
* Sourcemaps optional (`build.sourcemap=false` im Release).

### 2.2 Python: Dev-Deps trennen

Trenne Dependencies in:

* `core` (Runtime)
* `dev` (pytest, black, mypy, etc.)
* `extras` (webrelay/browser, llm, heavy)

→ Das spart nicht nur Größe, sondern verhindert “versehentlich importiert”.

### 2.3 PyInstaller onedir + clean data

* `onedir` statt `onefile`
* nur notwendige data files (static ui, schema json, migrations)
* Logs/DB nicht bundlen

**Gate:** SystemExercise muss grün sein.

---

## Stufe 3: Medium-Risk Shrink (immer noch gut kontrollierbar)

Jetzt kommt das, was du willst: “direkterer Weg”, aber ohne Zielverlust.

### 3.1 Import-Realität messen (ohne aggressives Entfernen)

Du lässt beim SystemExercise **Imports protokollieren**:

* Welche Module wurden überhaupt geladen?
* Welche “heavy” libs wurden nie berührt?

**Output:** `build/imports_used.txt`

Noch nichts entfernen – nur sichtbar machen.

### 3.2 “Excludes” nur für garantiert tote Standard-Libs

In vielen Bundles landen Standard-Libs, die du nie brauchst:

* `tkinter`, `tcl`, `test`, `unittest` (wenn du Runtime ohne tests willst),
* `distutils` (abhängig von Py version),
* `email` (wenn ungenutzt), `pydoc`, etc.

Aber: **nur nach Messung** und nur wenn SystemExercise + Smoke grün bleibt.

### 3.3 Lazy Imports für schwere Features

Wenn WebRelay/Browser/LLM nur selten gebraucht werden:

* Import erst in der Funktion, nicht global.
* Dadurch wird Core-Start schneller + PyInstaller zieht weniger rein.

**Seele bleibt gleich**, nur Körper atmet besser.

**Gate:** SystemExercise + “Feature-Probe” für optionalen Codepfad.

---

## Stufe 4: High-Impact, aber optional (nur wenn du willst)

### 4.1 Feature Packs als separate Wheels/ZIPs

Du kannst Features als “Pack” ausliefern:

* `sheratan_feature_webrelay.zip`
* `sheratan_feature_llm.zip`

Core erkennt: Pack vorhanden → aktiviert. Pack fehlt → Feature disabled, aber System läuft.

Damit kannst du **massiv** schrumpfen, ohne Fähigkeiten zu verlieren.

### 4.2 Nuitka (wenn PyInstaller nicht reicht)

Optional. Ich würde das erst anfassen, wenn du Stufe 1–3 stabil hast.

---

## Deine “Nicht zu viel abspecken”-Sicherung

Ich würde drei Schutzmechanismen einbauen:

1. **Regression Gate**: Build bricht ab, wenn SystemExercise nicht 100% durchläuft.
2. **Size Gate (soft)**: Wenn Größe plötzlich *zu stark* sinkt, ist das verdächtig → Review (weil dann evtl. Feature rausgefallen ist).
3. **Feature Matrix Report**: Build schreibt am Ende eine Tabelle:

   * Core features: ✅
   * Optional features detected: ✅/⚠️/❌
   * Reason: “pack missing”, “env missing”, “disabled by policy”

Das ist exakt dein “Ziel bleibt gleich, Weg wird direkter”.


* die genaue Repo-Dateistruktur für diese Pipeline,
* ein `system_exercise.py` Blueprint (konservativ, aber vollständig),
* ein `pyinstaller.spec` Grundgerüst mit **nur Low-Risk Defaults**,
* und einen CI-Job Ablauf (build → exercise → package → report).




 **PyInstaller · onedir · konservativ · regression-gesichert.**
Hier ist das **konkrete Startpaket**: Struktur, **SystemExercise**, **Spec-Skeleton**, **CI-Ablauf**. Ziel bleibt gleich – Weg wird direkter.

---

## 0) Repo-Layout (minimal, erweiterbar)

```
repo/
├─ core/
│  ├─ app.py                  # FastAPI app factory
│  ├─ runner.py               # claim → run → complete
│  ├─ policy.py               # allow/deny, routing
│  ├─ trace.py                # append-only decision trace
│  ├─ store.py                # sqlite + WAL
│  └─ __init__.py
├─ plugins/
│  ├─ read_file.py
│  ├─ write_file.py
│  ├─ walk_tree.py
│  └─ __init__.py
├─ ui/
│  ├─ dist/                   # Vite build output ONLY
│  └─ README.md
├─ schemas/
│  └─ decision_trace_v1.json
├─ tools/
│  └─ system_exercise.py      # 🔐 dein Sicherheitsnetz
├─ build/
│  ├─ pyinstaller.spec
│  ├─ manifest_baseline.json
│  └─ reports/
├─ requirements/
│  ├─ core.txt
│  ├─ extras.txt              # optional features
│  └─ dev.txt
├─ main.py                    # entrypoint (imports minimal!)
├─ pyproject.toml
└─ .github/workflows/build.yml
```

**Prinzip:** Core ist klein, **Extras sind Extras**, UI ist nur `dist/`.

---

## 1) `system_exercise.py` (konservativ, vollständig)

> Führt **alle Kernpfade einmal real** aus. Keine aggressiven Annahmen.

```python
# tools/system_exercise.py
import os, time, tempfile, requests, json, sqlite3
from pathlib import Path

BASE = os.environ.get("SHERATAN_BASE", "http://127.0.0.1:8001")

def ok(name, cond):
    print(f"[EXERCISE] {name}: {'OK' if cond else 'FAIL'}")
    if not cond:
        raise SystemExit(1)

def get(path):
    r = requests.get(f"{BASE}{path}", timeout=5)
    ok(f"GET {path}", r.status_code == 200)
    return r

def post(path, payload):
    r = requests.post(f"{BASE}{path}", json=payload, timeout=10)
    ok(f"POST {path}", r.status_code == 200)
    return r

def main():
    # 1) Health
    get("/api/system/health")

    # 2) DB/WAL check (lightweight: endpoint returns wal=true)
    r = get("/api/system/health")
    ok("WAL enabled", r.json().get("wal") is True)

    # 3) Job: read_file
    r = post("/api/jobs", {"kind":"read_file","params":{"path":"main.py"}})
    ok("read_file result", r.json().get("ok") is True)

    # 4) Job: write_file (temp)
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "x.txt"
        r = post("/api/jobs", {"kind":"write_file","params":{"path":str(p),"content":"hi"}})
        ok("write_file result", r.json().get("ok") is True)
        ok("file exists", p.exists())

    # 5) Job: walk_tree (repo root)
    r = post("/api/jobs", {"kind":"walk_tree","params":{"path":"."}})
    ok("walk_tree result", r.json().get("ok") is True)

    # 6) Trace written (exists & non-empty)
    trace = Path("data/decision_trace.jsonl")
    ok("trace exists", trace.exists())
    ok("trace non-empty", trace.stat().st_size > 0)

    # 7) UI asset reachable
    r = get("/index.html")
    ok("UI asset", "html" in r.headers.get("content-type",""))

    print("[EXERCISE] ALL GREEN")

if __name__ == "__main__":
    main()
```

**Gate:** Wenn DAS grün ist, darf geschrumpft werden. Punkt.

---

## 2) `pyinstaller.spec` (Low-Risk Defaults)

> Keine aggressiven Excludes. Onedir. Daten explizit.

```python
# build/pyinstaller.spec
from PyInstaller.utils.hooks import collect_submodules
block_cipher = None

hiddenimports = collect_submodules('core') + collect_submodules('plugins')

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('ui/dist', 'ui/dist'),
        ('schemas', 'schemas'),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    excludes=[
        # LOW-RISK ONLY (nach Exercise bestätigt)
        'tkinter', 'tcl', 'pydoc', 'test', 'unittest'
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    name='sheratan_core',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # konservativ
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='sheratan_core',
)
```

---

## 3) `main.py` (Import-Hygiene)

```python
# main.py
from core.app import create_app  # keine Heavy-Imports hier!

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
```

**Regel:** Heavy libs **nur** in Funktionsscope (lazy).

---

## 4) Dependencies (sauber getrennt)

**requirements/core.txt**

```
fastapi
uvicorn
pydantic
httpx
watchdog
sqlite-utils
structlog
```

**requirements/extras.txt**

```
# optional
playwright
numpy
```

**requirements/dev.txt**

```
pytest
black
mypy
```

---

## 5) CI-Workflow (Build → Exercise → Report)

```yaml
# .github/workflows/build.yml
name: build
on: [push]
jobs:
  win:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements/core.txt pyinstaller
      - run: npm ci && npm run build
        working-directory: ui
      - run: pyinstaller build/pyinstaller.spec
      - run: |
          dist\sheratan_core\sheratan_core.exe &
          timeout /t 5
          python tools/system_exercise.py
      - run: python tools/size_report.py
      - uses: actions/upload-artifact@v4
        with:
          name: sheratan_core_onedir
          path: dist/sheratan_core
```

*(Size-Report misst Ordnergröße, Filecount, Startzeit; Soft-Gate warnend.)*

---

## 6) Wie wir **konservativ schrumpfen**

1. **Baseline** (Size/Start/RAM) speichern.
2. **Exercise grün** → erlaubt.
3. **Nur** Low-Risk-Excludes.
4. Lazy Imports für Extras.
5. Optional: Feature-Packs als ZIPs.
6. **Nie** ohne Exercise.

---

## 7) Nächste sichere Ausbaustufe (optional)

* Import-Tracing während Exercise → **nur beobachten**.
* Feature-Matrix-Report (Core/Extras detected).
* UPX **erst**, wenn alles stabil.

---

Wenn du willst, mache ich **als Nächstes**:

* `size_report.py` + Import-Tracing (read-only),
* Feature-Pack-Loader (ZIP-based, hot-detect),
* oder eine **Noir-Dashboard-Kachel**, die den Exercise-Status live zeigt.

Du sagst nichts → ich mache **Import-Tracing + Size-Report** als nächsten Schritt.


Alles klar — dann kommt jetzt **Import-Tracing + Size-Report** (read-only, konservativ). Das ist genau der “direktere Weg”, ohne dass wir Funktionen riskieren.

---

## 1) `tools/import_trace.py` (Import-Realität mitschreiben)

* schreibt **nur** eine Liste der tatsächlich importierten Module
* kein Excluding, kein Eingriff in Laufzeitlogik

```python
# tools/import_trace.py

```

---

## 2) Einbau: **nur für Exercise / Debug**, nicht für normalen Betrieb

In `main.py` ganz oben (vor `create_app`) **optional**:

```python
# main.py (add near top)
import os

if os.environ.get("SHERATAN_IMPORT_TRACE") == "1":
    from tools.import_trace import install_import_tracer
    install_import_tracer()
```

**Warum so:** Du aktivierst es bewusst per Env-Flag. Kein Risiko im Normalbetrieb.

---

## 3) `tools/size_report.py` (Ordnergröße, Filecount, Top-Bloat)

* misst `dist/sheratan_core` (oder was du angibst)
* schreibt `build/reports/size_report.json`

```python
# tools/size_report.py
from __future__ import annotations

import json
import os
from pathlib import Path
from time import time

DEFAULT_DIST = Path("dist/sheratan_core")
OUT = Path("build/reports/size_report.json")

def dir_stats(root: Path) -> dict:
    total = 0
    files = 0
    biggest = []  # (size, relpath)

    for p in root.rglob("*"):
        if p.is_file():
            try:
                s = p.stat().st_size
            except OSError:
                continue
            total += s
            files += 1
            rel = str(p.relative_to(root)).replace("\\", "/")
            biggest.append((s, rel))

    biggest.sort(reverse=True)
    top = [{"bytes": s, "path": rel} for s, rel in biggest[:30]]

    return {
        "root": str(root).replace("\\", "/"),
        "bytes_total": total,
        "files_total": files,
        "top_30_files": top,
    }

def main():
    dist = Path(os.environ.get("SHERATAN_DIST", str(DEFAULT_DIST)))
    t0 = time()
    report = {
        "generated_at_unix": int(time()),
        "elapsed_ms": int((time() - t0) * 1000),
        "stats": dir_stats(dist),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[SIZE] wrote {OUT}")
    print(f"[SIZE] total_bytes={report['stats']['bytes_total']} files={report['stats']['files_total']}")
    print("[SIZE] top_5:")
    for x in report["stats"]["top_30_files"][:5]:
        print(f"  {x['bytes']:>10}  {x['path']}")

if __name__ == "__main__":
    main()
```

---

## 4) Running it (lokal & CI)

### Lokal

1. Start Core (wie immer)
2. Exercise mit Import-Trace:

**PowerShell**

```powershell
$env:SHERATAN_IMPORT_TRACE="1"
python tools/system_exercise.py
python tools/size_report.py
```

Output:

* `build/reports/imports_used.txt`
* `build/reports/size_report.json`

### CI (Windows)

Ergänze vor `python tools/system_exercise.py`:

```yaml
      - run: |
          set SHERATAN_IMPORT_TRACE=1
          python tools/system_exercise.py
          python tools/size_report.py
```

---

## 5) Wie wir daraus “konservativ shrinken” (ohne zu viel)

Ab jetzt ist die Logik:

1. **Baseline speichern** (erstes size_report + imports_used)
2. Änderungen machen (z.B. lazy imports / dev-deps trennen / exclude tkinter etc.)
3. **Exercise muss grün bleiben**
4. Größe darf sinken, aber wir entfernen nur Dinge, die:

   * (a) **nie importiert wurden** *und*
   * (b) **nicht zu einem optionalen Feature-Pack gehören**

Nächster Schritt danach wäre dann: **“Observed Exclude Suggestions”** (nur Vorschläge erzeugen, nix automatisch löschen).

---

Wenn du mir danach (nur copy-paste) die ersten ~30 Zeilen aus `imports_used.txt` und die `top_5` aus `size_report.py` gibst, kann ich dir sofort sagen, welche **Low-Risk** Kandidaten wir als nächstes rausnehmen (oder in Extras verschieben), ohne dass wir “zu viel” abspecken.
