# Sheratan - Autonomous Job Orchestration System

**Status**: Production-Ready Core | **Stand**: 2026-01-14

Ein autonomes Job-Orchestrierungs-System mit Mission/Task/Job Hierarchie, Offgrid Mesh und LLM-Integration.

---

## 🚀 Quick Start

```cmd
START_COMPLETE_SYSTEM.bat
```

Öffne Dashboard: **http://localhost:3001**

**Details**: Siehe [QUICKSTART.md](QUICKSTART.md)

---

## 📊 System-Übersicht

**8 Services** laufen auf festen Ports:

| Service | Port | Status |
|---------|------|--------|
| Core API | 8001 | ✅ Stabil |
| Broker | 9000 | ✅ Stabil |
| Host-A | 8081 | ✅ Stabil |
| Host-B | 8082 | ✅ Stabil |
| WebRelay | 3000 | ✅ Stabil |
| Dashboard | 3001 | ✅ Stabil |
| Worker Loop | - | ✅ Stabil |
| Chrome Debug | 9222 | ✅ Stabil |

---

## 📚 Dokumentation

### Einstieg
- **[QUICKSTART.md](QUICKSTART.md)** - System starten & erste Schritte
- **[system_overview.md](docs/system_overview.md)** - Alle Ports, API-Endpoints, IDE-Control

### Architektur
- **[PHASE_A_STATE_MACHINE.md](docs/PHASE_A_STATE_MACHINE.md)** - State Machine (PAUSED → OPERATIONAL → DEGRADED)
- **[MESH_CAPABILITIES.md](docs/MESH_CAPABILITIES.md)** - Mesh Network Details

### Status & Planung
- **[task.md](task.md)** - Aktuelle TODOs & Prioritäten
- **[SYSTEM_IST_DEFINITION.md](docs/SYSTEM_IST_DEFINITION.md)** - Was läuft aktuell
- **[PHASE2_DECISION_MATRIX.md](docs/PHASE2_DECISION_MATRIX.md)** - Geplante Optimierungen

---

## 🎯 Was funktioniert

**Production-Ready:**
- ✅ Mission/Task/Job Management (API)
- ✅ Dispatcher (automatische Job-Verteilung)
- ✅ ChainRunner (Spec→Job Erstellung)
- ✅ State Machine & Self-Diagnostics
- ✅ WHY-API (Decision Traces)

**Experimentell:**
- ⚠️ Crypto Sessions (vorbereitet, nicht aktiv)
- ⚠️ Encrypted Mesh Communication

---

## 📁 Struktur

```
c:\sauber_main\
├── core/                   # Core API (FastAPI)
├── mesh/offgrid/          # Mesh (Broker + Hosts)
├── worker/                # Worker Loop
├── external/webrelay/     # LLM Bridge
├── data/                  # Runtime Data
├── logs/                  # System Logs
├── docs/                  # Dokumentation
├── START_COMPLETE_SYSTEM.bat
└── STOP_SHERATAN.bat
```

---

## 🔧 Wichtige Commands

### System-Health prüfen
```powershell
Invoke-RestMethod http://localhost:8001/api/system/state
```

### Logs live ansehen
```powershell
Get-Content logs\state_transitions.jsonl -Tail 20 -Wait
```

### Mission erstellen
```powershell
$m = @{title="Test";description="Test";priority="normal"} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://localhost:8001/api/missions -Body $m -ContentType "application/json"
```

**Mehr Commands**: Siehe [system_overview.md](docs/system_overview.md)

---

## 🛑 System stoppen

```cmd
STOP_SHERATAN.bat
```

---

## 🚨 Troubleshooting

**Port bereits belegt:**
```cmd
STOP_SHERATAN.bat
timeout /t 5
START_COMPLETE_SYSTEM.bat
```

**Core API antwortet nicht:**  
Warte 60 Sekunden nach Start - Services brauchen Zeit.

**Mehr Hilfe**: Siehe [QUICKSTART.md](QUICKSTART.md#troubleshooting)

---

## 📞 Support

- **Logs**: `logs/`
- **State**: `runtime/system_state.json`
- **Data**: `data/`
