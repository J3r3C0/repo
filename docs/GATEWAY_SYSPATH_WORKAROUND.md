# Gateway Integration - sys.path Workaround

## Current Implementation

The gateway middleware (`core/gateway_middleware.py`) currently adds the repo root to `sys.path` at runtime:

```python
# Ensure mesh package is importable (add repo root to path)
_repo_root = Path(__file__).parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))
```

## Why This Works

This allows `mesh.core.gates` to be imported regardless of how Core is started (from any directory).

## Why This Is Fragile

- **Packaging conflicts:** Can shadow other modules if repo root contains conflicting names
- **Test isolation:** Breaks in some test environments where sys.path manipulation is restricted
- **Deployment:** Won't work in containerized/packaged deployments without modification

## Recommended Solutions

### Option A: Start Core with PYTHONPATH (Immediate)

**In `START_COMPLETE_SYSTEM.bat` or Core startup script:**
```powershell
$env:PYTHONPATH = "C:\sauber_main"
python -m core.main
```

**Or on Linux/Mac:**
```bash
PYTHONPATH=/path/to/sauber_main python -m core.main
```

### Option B: Editable Install (Best Practice)

**One-time setup in repo root:**
```bash
pip install -e .
```

**Requires `setup.py` or `pyproject.toml`:**
```python
# setup.py
from setuptools import setup, find_packages

setup(
    name="sheratan",
    version="2.0.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        # ... other deps
    ]
)
```

Then `mesh` is always importable, no sys.path hacks needed.

### Option C: Move Gates to Core (Alternative)

Copy `mesh/core/gates/` to `core/gates/` and import directly:
```python
from core.gates.pipeline import run_gates_v1
```

## Current Status

✅ **sys.path workaround is functional** - system works as-is
⏸️ **Migration to proper solution** - deferred to Phase 2

## Action Items

- [ ] Document recommended startup method (`python -m core.main` with PYTHONPATH)
- [ ] Create `setup.py` for editable install
- [ ] Test with editable install
- [ ] Remove sys.path hack once editable install is verified
- [ ] Update all startup scripts to use proper method
