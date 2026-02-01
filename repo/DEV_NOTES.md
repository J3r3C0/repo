# Sheratan Development Notes

## Critical Knowledge

### PYTHONPATH
**MUST** be set to repo root (`%~dp0`) before starting Python services.
- Without it: `ModuleNotFoundError: No module named 'core'`
- Reason: Python needs to resolve `from core.xxx import yyy`
- Set in: `START_HUB.bat` before starting Core/Broker

### Chrome Profile Path
**MUST** use absolute path, not relative.
- Relative path (`data/chrome_profile`) → "cannot read/write" error
- Absolute path (`%~dp0data\chrome_profile`) → works
- Reason: Chrome CWD may differ from script CWD

### Chrome Debug Port
Port **9222** is required for Puppeteer (WebRelay).
- WebRelay connects via `puppeteer.connect({ browserURL: 'http://127.0.0.1:9222' })`
- Without debug port: WebRelay can't execute LLM jobs
- Sessions saved in profile → login persists across restarts

### Service Dependencies
```
Chrome (9222) ← MUST start first
  ↓
WebRelay (3000) ← Needs Chrome
  ↓
Hub (Core 8001) ← Dispatcher inside Core
```

### Dispatcher
- **Integrated in Core** (not separate process)
- Runs in background thread (started in `lifespan`)
- Polls every 2 seconds for pending jobs
- Writes jobs to `runtime/input/` for workers

### ChainRunner
- **Integrated in Core** (background thread)
- Converts specs → jobs
- Polls `chain_specs` table every 1 second
- Resolves result-refs before creating jobs

## Common Issues

### Job stays "pending"
1. Check Dispatcher running: `sheratan health`
2. Check `runtime/input/` for job files
3. Check worker registered: `curl http://localhost:8001/api/mesh/workers`

### Chrome "cannot read/write profile"
- Fix: Use absolute path in `--user-data-dir`
- Check: `START_CHROME.bat` uses `%~dp0data\chrome_profile`

### ModuleNotFoundError
- Fix: Set `PYTHONPATH=%~dp0` before `python -u core\main.py`
- Check: `START_HUB.bat` sets PYTHONPATH

### WebRelay can't connect to Chrome
- Fix: Start Chrome first with `--remote-debugging-port=9222`
- Check: `Test-NetConnection localhost -Port 9222`

## File Locations

- **Job Queue:** `runtime/input/*.json` (written by Dispatcher)
- **Job Results:** `runtime/output/*.json` (written by Workers)
- **Ledger:** `runtime/output/ledger.jsonl` (job events)
- **Chrome Profile:** `data/chrome_profile/` (persistent sessions)
- **Logs:** `logs/*.log`, `logs/*.jsonl`

## Port Map

| Service | Port | Purpose |
|---------|------|---------|
| Chrome | 9222 | Debug/CDP for Puppeteer |
| Core | 8001 | Main API + Dispatcher |
| Broker | 9000 | Mesh coordination |
| WebRelay | 3000 | LLM worker |
| Dashboard | 3001 | UI |
