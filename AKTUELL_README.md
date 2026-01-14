# Sheratan System - Aktueller Stand

**Stand**: 2026-01-14  
**Status**: Läuft stabil, einige Features experimentell

---

## Was ist Sheratan?

Ein **autonomes Job-Orchestrierungs-System** mit:
- Mission/Task/Job Hierarchie
- Offgrid Mesh (Broker + Worker Nodes)
- LLM-Integration (ChatGPT/Gemini)
- State Machine für System-Health
- Self-Diagnostics & Anomaly Detection

---

## 🚀 System starten (3 Schritte)

### 1. System starten
```cmd
START_COMPLETE_SYSTEM.bat
```

Das startet **8 Services** in dieser Reihenfolge:
1. Chrome Debug (Port 9222)
2. Core API (Port 8001)
3. Broker (Port 9000)
4. Host-A (Port 8081)
5. Host-B (Port 8082)
6. WebRelay (Port 3000)
7. Worker Loop
8. Dashboard (Port 3001)

**Dauer**: ~60 Sekunden bis alles läuft

### 2. Dashboard öffnen
```
http://localhost:3001
```

### 3. System prüfen
```powershell
# System State
Invoke-RestMethod http://localhost:8001/api/system/state

# Jobs anzeigen
Invoke-RestMethod http://localhost:8001/api/jobs
```

---

## 📊 Service-Übersicht

| Service | Port | Zweck | Status |
|---------|------|-------|--------|
| **Core API** | 8001 | Mission/Task/Job Management | ✅ Stabil |
| **Broker** | 9000 | Job-Auktion & Routing | ✅ Stabil |
| **Host-A** | 8081 | Worker Node A | ✅ Stabil |
| **Host-B** | 8082 | Worker Node B | ✅ Stabil |
| **WebRelay** | 3000 | LLM-Bridge (ChatGPT) | ✅ Stabil |
| **Worker Loop** | - | Job-Processor | ✅ Stabil |
| **Dashboard** | 3001 | Web UI | ✅ Stabil |
| **Chrome Debug** | 9222 | CDP für WebRelay | ✅ Stabil |

---

## 🎯 Was funktioniert

### ✅ Core Features (Production-Ready)
- Mission/Task/Job CRUD (API)
- Dispatcher (automatische Job-Verteilung)
- ChainRunner (Spec→Job Erstellung)
- State Machine (PAUSED → OPERATIONAL → DEGRADED)
- Self-Diagnostics (Health Checks)
- Anomaly Detection
- Performance Baselines
- WHY-API (Decision Traces)

### ⚠️ Experimentell (Vorbereitet, nicht aktiv)
- Crypto Sessions (upgraded, aber nicht im Live-Mesh genutzt)
- Encrypted Mesh Communication
- Replay Protection (Code da, ungetestet)

---

## 📁 Wichtige Verzeichnisse

```
c:\sauber_main\
├── core/                   # Core API (FastAPI)
│   ├── main.py            # Haupteinstieg
│   ├── state_machine.py   # System State
│   ├── dispatcher.py      # Job Dispatcher (in main.py)
│   └── why_api.py         # Explainability API
├── mesh/offgrid/          # Mesh Network
│   ├── broker/            # Auction API
│   ├── host/              # Worker Nodes
│   └── crypto/            # Session Crypto (experimentell)
├── worker/                # Worker Loop
│   └── worker_loop.py
├── external/webrelay/     # LLM Bridge
├── data/                  # Runtime Data
│   ├── missions/          # Mission Files
│   ├── tasks/             # Task Files
│   ├── jobs/              # Job Files
│   └── webrelay_out/      # LLM Job Queue
├── logs/                  # System Logs
│   ├── state_transitions.jsonl
│   └── decision_trace_v1.jsonl
└── runtime/               # Runtime State
    └── system_state.json
```

---

## 🔧 Wichtige API-Endpunkte

### System Health
```http
GET  /api/system/state              # Aktueller System-State
POST /api/system/state/transition   # State ändern
GET  /api/system/state/history      # State-Historie
GET  /api/diagnostics/status        # Self-Diagnostics
```

### Missions & Jobs
```http
GET  /api/missions                  # Alle Missions
POST /api/missions                  # Mission erstellen
GET  /api/jobs                      # Alle Jobs
POST /api/jobs/{id}/sync            # Job-Result abholen
```

### Explainability (WHY-API)
```http
GET /api/why/latest?intent=dispatch_job  # Letzte Entscheidung
GET /api/why/stats                       # Decision Statistics
```

---

## 🛑 System stoppen

```cmd
STOP_SHERATAN.bat
```

Oder manuell alle CMD-Fenster schließen.

---

## 📖 Weitere Dokumentation

### Aktuell & Relevant
- **[system_overview.md](file:///C:/Users/jerre/.gemini/antigravity/brain/7047d09f-2964-4d0c-b0dd-35d881281562/system_overview.md)** - Port-Map & IDE-Control (neu erstellt)
- **[docs/PHASE_A_STATE_MACHINE.md](file:///c:/sauber_main/docs/PHASE_A_STATE_MACHINE.md)** - State Machine Details
- **[docs/SYSTEM_IST_DEFINITION.md](file:///c:/sauber_main/docs/SYSTEM_IST_DEFINITION.md)** - System-Ist-Zustand

### Historisch (Referenz)
- **[archive/README.md](file:///c:/sauber_main/archive/README.md)** - Offgrid-Net v0.16-alpha (alte Basis)
- **[docs/SHERATAN_REFACTORING_PLAN.md](file:///c:/sauber_main/docs/SHERATAN_REFACTORING_PLAN.md)** - Geplante Features

---

## ⚡ Quick Commands

### System prüfen
```powershell
# Alle Ports testen
$ports = @(8001, 9000, 3000, 3001, 8081, 8082)
foreach ($p in $ports) {
    try {
        Invoke-WebRequest "http://localhost:$p" -TimeoutSec 1 -UseBasicParsing
        Write-Host "✅ Port $p - OK" -ForegroundColor Green
    } catch {
        Write-Host "❌ Port $p - DOWN" -ForegroundColor Red
    }
}
```

### Logs live ansehen
```powershell
# State Transitions
Get-Content logs\state_transitions.jsonl -Tail 20 -Wait

# Decision Traces
Get-Content logs\decision_trace_v1.jsonl -Tail 10 -Wait
```

### Mission erstellen
```powershell
$mission = @{
    title = "Test Mission"
    description = "Testing"
    priority = "normal"
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri http://localhost:8001/api/missions `
    -Body $mission -ContentType "application/json"
```

---

## 🚨 Troubleshooting

### "Port already in use"
```cmd
STOP_SHERATAN.bat
timeout /t 5
START_COMPLETE_SYSTEM.bat
```

### "Core API not responding"
Warte 30-60 Sekunden nach Start - Services brauchen Zeit zum Hochfahren.

### "Dashboard zeigt keine Daten"
1. Prüfe Core API: `http://localhost:8001/api/system/state`
2. Prüfe Browser-Console (F12)
3. Dashboard neu laden (Ctrl+F5)

---

## 🎓 Nächste Schritte

### Für Entwicklung
1. ✅ System läuft
2. ⏳ Crypto-Sessions testen (wenn gewünscht)
3. ⏳ Encrypted Mesh aktivieren (experimentell)

### Für Produktion
1. ⏳ Burn-In Tests (siehe [docs/PHASE1_BURN_IN_TEST_PLAN.md](file:///c:/sauber_main/docs/PHASE1_BURN_IN_TEST_PLAN.md))
2. ⏳ Performance-Optimierung
3. ⏳ Multi-Node Setup

---

## 📞 Support

**Logs**: `c:\sauber_main\logs\`  
**State**: `c:\sauber_main\runtime\system_state.json`  
**Data**: `c:\sauber_main\data\`

Bei Problemen: Logs prüfen, State Machine Status checken, Services neu starten.
