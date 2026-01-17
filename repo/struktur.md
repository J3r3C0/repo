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
