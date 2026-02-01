# Sheratan Architecture (v1.1)

## Overview

Sheratan verwendet eine **Embedded Hub Architecture**, bei der Hub-Funktionalität in `core/` und `mesh/` integriert ist, statt als separater Service zu laufen.

```
┌─────────────────────────────────────────┐
│  Sheratan Core (repo/)                  │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │  core/main.py                    │  │
│  │  - Orchestration                 │  │
│  │  - Dispatcher (Hub Queue Mgr)    │  │
│  │  - State Machine                 │  │
│  │  - MCTS Decision Engine          │  │
│  └──────────────────────────────────┘  │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │  mesh/registry/                  │  │
│  │  - Node Registry (Hub Registry)  │  │
│  │  - Ledger Service                │  │
│  │  - Replica Sync                  │  │
│  └──────────────────────────────────┘  │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │  core/webrelay_bridge.py         │  │
│  │  - Job Queue (Hub Gateway)       │  │
│  │  - Worker Communication          │  │
│  └──────────────────────────────────┘  │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │  Trust & Integrity               │  │
│  │  - core/attestation.py           │  │
│  │  - core/idempotency.py           │  │
│  │  - core/result_integrity.py      │  │
│  └──────────────────────────────────┘  │
└─────────────────────────────────────────┘
           │
           │ File-based Queue
           ▼
    ┌──────────────┐
    │ webrelay_out/│
    └──────────────┘
           │
           ▼
    External Workers
```

## Hub-Verantwortlichkeiten (Embedded)

### 1. Gateway & Queue Management
**Location:** `core/main.py` → `Dispatcher` class (Zeilen 243-505)

**Funktionen:**
- Job-Queue mit Prioritäten (critical/high/normal)
- Dependency Resolution
- Retry mit Exponential Backoff
- Gate Enforcement (G0-G4)
- Autonomous Settlement

**Equivalent zu:** `gemmaloop/hub/serve_gateway.py` + `queue_manager.py`

---

### 2. Node Registry
**Location:** `mesh/registry/mesh_registry.py`

**Funktionen:**
- Worker/Node-Registrierung
- Capability-Tracking
- Performance-Statistiken (EMA)
- Health-Status

**Equivalent zu:** `gemmaloop/hub/registry.py`

---

### 3. Attestation & Trust
**Location:** `core/attestation.py`

**Funktionen:**
- Node-Identitäts-Validierung
- Build-ID-Tracking
- Capability-Hash-Verification
- Drift-Detection

**Equivalent zu:** `gemmaloop/hub/attestation.py`

---

### 4. Idempotency
**Location:** `core/idempotency.py`

**Funktionen:**
- Request-Deduplication
- Payload-Hash-Verification
- Collision-Detection

**Equivalent zu:** `gemmaloop/hub/idempotency.py`

---

### 5. Result Integrity
**Location:** `core/result_integrity.py`

**Funktionen:**
- Hash-Verification von Worker-Results
- Tamper-Detection

**Equivalent zu:** `gemmaloop/hub/result_integrity.py`

---

### 6. Metrics & Diagnostics
**Location:** 
- `core/self_diagnostics.py`
- `mesh/core/metrics_client.py`
- `core/performance_baseline.py`

**Funktionen:**
- Performance-Baselines
- Anomaly-Detection
- Health-Scoring
- SLO-Monitoring

**Equivalent zu:** `gemmaloop/hub/metrics.py`

---

## Warum Embedded Hub?

### Vorteile:
✅ **Einfacheres Deployment** - Ein Prozess statt zwei  
✅ **Weniger Latenz** - Keine Netzwerk-Hops zwischen Core und Hub  
✅ **Atomare Transaktionen** - Dispatcher und Registry im selben Prozess  
✅ **Einfacheres Debugging** - Ein Log-Stream  

### Trade-offs:
⚠️ **Weniger Skalierbarkeit** - Hub kann nicht unabhängig skalieren  
⚠️ **Tighter Coupling** - Core und Hub-Logik im selben Modul  

---

## API-Mapping: Embedded vs. Separate Hub

| Hub-Funktion | Separate Hub (gemmaloop) | Embedded Hub (sauber_main) |
|--------------|--------------------------|----------------------------|
| **Node Registry** | `GET /registry` | `mesh.registry.mesh_registry.WorkerRegistry` |
| **Heartbeat** | `POST /mesh/heartbeat` | Integriert in Dispatcher |
| **Job Queue** | `GET /mesh/pull_requests` | `webrelay_bridge.enqueue_job()` |
| **Result Ingest** | `POST /mesh/submit_result` | `webrelay_bridge.try_sync_result()` |
| **Attestation** | `evaluate_attestation()` | `core.attestation.verify_attestation()` |
| **Metrics** | `GET /metrics` | `core.self_diagnostics.get_latest_report()` |

---

## Startup-Sequenz

```python
# repo/main.py
app = create_app()  # FastAPI

# core/main.py lifespan()
async def lifespan(app):
    # 1. Initialize Storage
    storage.init_db()
    
    # 2. Initialize Hub Components (embedded)
    webrelay_bridge = WebRelayBridge()  # Gateway
    dispatcher = Dispatcher(bridge=webrelay_bridge)  # Queue Manager
    slo_manager = SLOManager()  # Monitoring
    
    # 3. Start Background Tasks
    asyncio.create_task(dispatcher.run_loop())
    asyncio.create_task(slo_manager.run_loop())
    
    yield
    
    # Cleanup
    dispatcher.stop()
    slo_manager.stop()
```

---

## Migration zu Separate Hub (Future: v1.2)

Falls später Skalierung erforderlich:

1. **Extrahiere** `core/main.py:Dispatcher` → `hub/queue_manager.py`
2. **Extrahiere** Hub-APIs aus `core/main.py` → `hub/serve_gateway.py`
3. **Starte** Hub als separaten Prozess (Port 8002)
4. **Update** `core/main.py` → Delegiert an Hub-HTTP-API

**Breaking Changes:** Minimal (nur interne Routing-Logik)

---

## Zusammenfassung

**Sheratan v1.1 = Embedded Hub Architecture**

- Hub-Funktionalität verteilt über `core/` und `mesh/`
- Funktional equivalent zu separatem Hub
- Optimiert für Single-Node-Deployment
- Migrierbar zu Multi-Hub bei Bedarf
