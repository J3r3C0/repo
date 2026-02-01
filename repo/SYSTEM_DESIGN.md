# Sheratan System Design v1.0

**Status:** Phase 2 Complete (2026-01-18)  
**Architecture:** Hub-and-Spoke with Autonomous Job Chaining

---

## Architecture Overview


┌─────────────────────────────────────────────────────────────┐     
│                                                             │    
   ┌──────────────┐  ┌──────────────┐   ┌─────────────────┐     │     
│  │   Core API   │  │    │hub  │   │---│      ChainRunner│     │     
│  │  (Port 8001) ──│                |   |                |     |   
│  └──────────────┘  └────────|──────┘  └─────────────────┘     │     
│         │              ┌──────────────┐         │             │     
│         └──────────────|Dispatcher     ┴────────              |
│                        └──────────────┘          |            │     
└────────────────────────────┼──────────────────────|──────────┘     
                             │                     |               
        ┌────────────────────┼────────────────────┐                
        │                    │                    │                
   │ WebRelay│        │   Broker    │     │  Dashboard  │
   │ Worker  │        │ (Port 9000) │     │ (Port 3001) │
   │(Port3000)│        └─────────────┘     └─────────────┘           
   └─────────
        │
   ┌────▼────┐
   │ Chrome  │
   │(Port9222)│
   └─────────┘
```

---

## Core Components

### 1. Core API (Port 8001)
**File:** `core/main.py`  
**Purpose:** Central orchestration hub

**Responsibilities:**
- Mission/Task/Job CRUD
- Job lifecycle management
- LCP parsing and follow-up job creation
- Gateway enforcement (G0-G4)
- Metrics collection
- Health monitoring

**Key Endpoints:**
- `POST /api/missions` - Create mission
- `POST /api/tasks/{id}/jobs` - Create job
- `POST /api/jobs/{id}/sync` - Sync job result
- `POST /api/jobs/{id}/dispatch` - Manual dispatch
- `GET /api/health` - Health check
- `GET /api/system/metrics` - System metrics

**Storage:**
- SQLite: `data/sheratan.db`
- Schemas: Mission, Task, Job, ChainContext, ChainSpec

---

### 2. Dispatcher (Background Thread)
**File:** `core/main.py` (class Dispatcher)  
**Purpose:** Automatic job distribution to workers

**Flow:**
1. Poll pending jobs every 2 seconds
2. Check dependencies (all `depends_on` completed)
3. Apply backpressure (max inflight limit)
4. Call `bridge.enqueue_job(job_id)`
5. Update job status: `pending` → `working`

**Backpressure:**
- `MAX_INFLIGHT`: 100 jobs
- `MAX_QUEUE_DEPTH`: 1000 jobs

**Current Issue:** 🔴 Jobs not being dispatched (blocker)

---

### 3. ChainRunner (Background Thread)
**File:** `core/chain_runner.py`  
**Purpose:** Convert job specs → actual jobs

**Flow:**
1. Poll `chain_specs` table every 1 second
2. Claim pending spec (with lease)
3. Resolve parameters (result-refs, artifacts)
4. Create Job entity
5. Mark spec as dispatched

**Spec Resolution:**
- Template strings: `${job.result.data}`
- Artifact refs: `paths_from_artifact`
- Job result refs: `inputs_from_job_result`

---

### 4. WebRelay Bridge
**File:** `core/webrelay_bridge.py`  
**Purpose:** Job file I/O for workers

**Paths:**
- **Jobs OUT:** `runtime/narrative/` (WebRelay watches this)
- **Results IN:** `runtime/output/` (WebRelay writes here)

**Job Envelope (v1):**
```json
{
  "schema_version": "job_envelope_v1",
  "job_id": "...",
  "kind": "agent_plan",
  "params": {...},
  "refs": {
    "mission_id": "...",
    "task_id": "...",
    "chain_id": "...",
    "trace_id": "..."
  }
}
```

**Recent Fix:** Changed paths from `data/webrelay_out/` to `runtime/narrative/` <--späterhttp://localhost:3000/status>

---

### 5. WebRelay Worker (Port 3000)  
**File:** `external/webrelay/index.ts`  
**Purpose:** LLM execution via browser automation

**Capabilities:**
- `llm_call` (cost: 25)
- `agent_plan` (cost: 30)
- `analyze_file` (cost: 20)

**Backend:** ChatGPT or Gemini (via Puppeteer) <(später dual llm mit routing fallback oder specs "diffrent parsing types")

**Flow:**
1. Watch `runtime/narrative/` for `.json` files
2. Parse job envelope
3. Build prompt from job params
4. Call LLM via Chrome CDP (port 9222)
5. Parse response
6. Write result to `runtime/output/{job_id}.result.json`(http + file)

**Result Envelope (v1):**
```json <ausbaubedürftig>
{
  "schema_version": "result_envelope_v1",
  "job_id": "...",
  "ok": true,
  "result": {
    "summary": "...",
    "data": {...}
  },
  "metrics": {
    "execution_time_ms": 1234,
    "llm_backend": "chatgpt"
  }
}
```

---

### 6. Chrome (Port 9222)
**Purpose:** Browser for LLM interaction

**Launch:**
```bash
chrome.exe --remote-debugging-port=9222 \
           --user-data-dir=data/chrome_profile \
           https://chatgpt.com \
           https://gemini.google.com
```

**Profile:** `data/chrome_profile/` (persistent sessions)

**Critical:** Must use **path** for profile!

---

### 7. Broker (Port 9000)
**File:** `mesh/offgrid/broker/broker_real.py`  
**Purpose:** Mesh worker discovery and reputation

**Config:** `mesh/offgrid/discovery/mesh_hosts.json`

**Flow:**
1. Load hosts from `mesh_hosts.json`
2. Ping each host's `/status` endpoint
3. Update reputation (±0.05 per ping)
4. Rank hosts by reputation

**Current Issue:** 🟡 No hosts running (needs node-A or WebRelay in hosts list) (host=piont of work)

---

### 8. Dashboard (Port 3001)
**File:** `external/dashboard/`  
**Purpose:** UI for monitoring

**Features:**
- Mission/Task/Job overview
- Live logs
- Mesh worker status
- System metrics

---

## Data Flow

**richtig**, a **klare Ebenen**, **saubere Benennung**  **keine Vermischung von Verantwortlichkeiten**.
**sachliche, lineare Ordnung**,**lesen, implementieren und testen**

Ich trenne bewusst:

* **API / Control Plane**
* **Execution / Data Plane**
* **Chain Logic**

---

## E2E Mission Flow – Zielzustand (klar & stabil)

### Phase A — Definition (Control Plane / User → Core)

**A1. Mission anlegen**

```
POST /api/missions
→ Mission{id}
```

**A2. Task anlegen**

```
POST /api/missions/{mission_id}/tasks
→ Task{id}
```

**A3. Initialen Job anlegen (agent_plan)**

```
POST /api/tasks/{task_id}/jobs
Body: { kind: "agent_plan", params: ... }
→ Job{id, status=pending}
```

👉 Ergebnis Phase A:

* Mission, Task, **1 Root-Job**
* Alles **persistiert im Core**
* Noch **keine Ausführung**

---

### Phase B — Dispatch (Execution Start / Core intern)

**B1. Dispatcher erkennt pending Job**

* Pollt Job-Tabelle
* Wählt nächsten `status=pending`

**B2. Dispatcher initialisiert Ausführung**

* `bridge.enqueue_job(job)`
* Persistiert Job-Narrativ:

```
runtime/narrative/{job_id}.job.json
```

**B3. Jobstatus**

```
pending → working
```

👉 Ergebnis Phase B:

* Job ist **zur Ausführung freigegeben**
* Core bleibt **Owner des Zustands**
* Externe Worker arbeiten **nur auf Kopien**

---

### Phase C — Externe Verarbeitung (WebRelay / LLM)

**C1. WebRelay liest Job-Narrativ**

```
runtime/narrative/{job_id}.job.json
```

**C2. WebRelay führt Job aus**

* Ruft LLM (ChatGPT / Gemini / Stub)
* Erzeugt LCP-konforme Antwort

**C3. WebRelay schreibt Ergebnis**

```
runtime/output/{job_id}.result.json
```

👉 Wichtig:

* **WebRelay schreibt keinen Core-State**
* **Kein Direktzugriff auf DB**
* Nur Files als Übergabe

---

### Phase D — Result Sync (Execution → Control Plane)

**D1. Result-Sync wird ausgelöst**

```
POST /api/jobs/{job_id}/sync
```

(automatisch durch WebRelay oder per Polling)

**D2. Core verarbeitet Result**

* Liest `runtime/output/{job_id}.result.json`
* Validiert & parst LCP Envelope
* Persistiert Ergebnis

**D3. Jobstatus**

```
working → completed
```

👉 Ergebnis Phase D:

* Job abgeschlossen
* Ergebnis **offiziell im Core**

---

### Phase E — Chain-Auswertung (Chain Logic)

**E1. LCP Parser analysiert Result**

* `parse_lcp(result)`
* Prüft auf Struktur:

  * `type: followup_jobs`
  * `type: final_answer`

---

### Phase F — Follow-up Jobs (falls vorhanden)

**F1. Follow-up Specs extrahieren**

```
{ type: "followup_jobs", jobs: [...] }
```

**F2. Specs registrieren**

* `chain_manager.register_followup_specs()`
* Speicherung in:

```
chain_specs table
```

👉 Wichtig:

* Specs ≠ Jobs
* Noch **keine Ausführung**

---

### Phase G — ChainRunner (Specs → Jobs)

**G1. ChainRunner pollt chain_specs**

* Sucht unresolved Specs

**G2. Auflösung & Materialisierung**

* Resolves Result-Refs
* Erzeugt neue Job-Entities

**G3. Neue Jobs**

```
status = pending
```

➡️ Rücksprung zu **Phase B (Dispatcher)**

---

### Phase H — Abschluss der Chain

**H1. LCP liefert final_answer**

```
{ type: "final_answer", answer: {...} }
```

**H2. Core markiert Chain**

```
chain.status = completed
```

**H3. Mission / Task abgeschlossen**

* Keine weiteren Jobs
* Endzustand stabil

---

## Kurzfassung als mentale Checkliste

1. **API erzeugt nur Struktur** (Mission / Task / Job)
2. **Dispatcher startet Ausführung**
3. **Externe Worker arbeiten file-basiert**
4. **Core synchronisiert Ergebnisse**
5. **Chain-Logik erzeugt neue Jobs**
6. **Loop bis final_answer**

---

## Architekturelle Klarstellung (wichtig!)

* **Core**
  besitzt *State, Status, Chain, Wahrheit*

* **WebRelay / Worker**
  führen aus, **besitzen nichts**

* **Files (runtime/)**
  sind **Transport**, kein State

* **ChainRunner**
  ist **Materialisierer**, kein Denker

---

## File Structure

```
repo/
├── core/
│   ├── main.py              # Core API + Dispatcher
│   ├── webrelay_bridge.py   # Job I/O
│   ├── chain_runner.py      # Spec→Job conversion
│   ├── job_chain_manager.py # Chain orchestration
│   ├── lcp_actions.py       # LCP parsing
│   ├── robust_parser.py     # LLM response parsing
│   ├── metrics_client.py    # Telemetry
│   ├── storage.py           # DB operations
│   └── config.py            # Configuration
│
├── mesh/
│   └── offgrid/
│       ├── broker/
│       │   └── broker_real.py
│       └── discovery/
│           └── mesh_hosts.json
│
├── external/
│   ├── webrelay/
│   │   ├── index.ts         # Worker main
│   │   ├── backends/
│   │   │   ├── chatgpt.ts
│   │   │   └── gemini.ts
│   │   └── parser.ts
│   └── dashboard/
│
├── runtime/
│   ├── narrative/           # Jobs OUT (Core → Worker)
│   ├── output/              # Results IN (Worker → Core)
│   └── archive/             # Completed jobs
│
├── data/
│   ├── sheratan.db          # SQLite database
│   ├── chrome_profile/      # Chrome sessions
│   └── chains/              # Chain state files
│
├── START_HUB.bat            # Start Core + Broker
├── START_CHROME.bat         # Start Chrome
├── START_WEBRELAY.bat       # Start WebRelay
├── START_DASHBOARD.bat      # Start Dashboard
└── sheratan.bat             # CLI tool
```

---

## Configuration

### Environment Variables
- `PYTHONPATH` - **CRITICAL:** Must be set to repo root
- `BROWSER_URL` - Chrome CDP URL (default: `http://127.0.0.1:9222`)
- `LLM_BACKEND` - `chatgpt` or `gemini`
- `SHERATAN_BUILD_ID` - Build identifier
- `SHERATAN_NODE_ID` - Node identifier

### Config Files
- `config/gateway_config.json` - Gateway enforcement rules
- `mesh/offgrid/discovery/mesh_hosts.json` - Worker discovery
- `mesh/registry/workers.json` - Worker capabilities

---

## Critical Knowledge

### PYTHONPATH
**MUST** be set to repo root before starting Python services.
```batch
set PYTHONPATH=%~dp0
```
Without it: `ModuleNotFoundError: No module named 'core'`

### Chrome Profile Path
**MUST** use absolute path:
```batch
--user-data-dir="%~dp0data\chrome_profile"
```
Relative paths cause "cannot read/write" errors.

### Service Dependencies
```
Chrome (9222) ← MUST start first
  ↓
WebRelay (3000) ← Needs Chrome
  ↓
Hub (Core 8001) ← Dispatcher inside Core
```

---

## Current Status

### ✅ Working
- Core API (all endpoints)
- Mission/Task/Job CRUD
- LCP parsing
- ChainRunner (spec→job conversion)
- WebRelay worker
- Chrome integration
- Gateway enforcement (soft mode)
- Metrics collection
- Health endpoints

### 🔴 Blockers
1. **Dispatcher not dispatching jobs**
   - Jobs stay `pending`
   - `bridge.enqueue_job()` not called
   - No files in `runtime/narrative/`

### 🟡 Warnings
1. **Broker has no hosts**
   - Needs node-A or WebRelay in `mesh_hosts.json`
   - Not critical for E2E flow

---

## Next Steps

1. **Debug Dispatcher**
   - Check if thread is running
   - Check if `_dispatch_step()` is called
   - Add logging to `bridge.enqueue_job()`

2. **Test E2E Flow**
   - Create mission → task → job
   - Verify file in `runtime/narrative/`
   - Verify WebRelay processes it
   - Verify result synced
   - Verify follow-up jobs created

3. **Start Hosts (Optional)**
   - Start node-A for Broker
   - Or: Add WebRelay to `mesh_hosts.json`

---

## CLI Commands

```bash
# Start services
sheratan start chrome      # Chrome with debug port
sheratan start hub         # Core + Broker + Dispatcher
sheratan start webrelay    # WebRelay worker
sheratan start dashboard   # Dashboard UI
sheratan start all         # Everything

# Stop services
sheratan stop chrome       # Stop Chrome
sheratan stop core         # Stop Core
sheratan stop              # Stop all

# Health check
sheratan health            # Check all services

# System status
sheratan status            # Get detailed status

# View logs
sheratan logs core.log     # View specific log
```

---

## Port Map

| Service | Port | Purpose |
|---------|------|---------|
| Chrome | 9222 | Debug/CDP for Puppeteer |
| Core | 8001 | Main API + Dispatcher |
| Broker | 9000 | Mesh coordination |
| WebRelay | 3000 | LLM worker |
| Dashboard | 3001 | UI |

---

**Last Updated:** 2026-01-18 01:55  
**Version:** 1.0 (Phase 2 Complete)
