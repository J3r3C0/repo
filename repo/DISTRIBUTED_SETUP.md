# Sheratan Distributed Setup

## Architektur

```
┌─────────────────────────────────────┐
│  DIESER RECHNER (Hub)               │
│  ├─ Core API (8001)                 │
│  ├─ Broker (9000)                   │
│  ├─ Node-A (8081) ← lokaler Worker │
│  ├─ WebRelay (3000)                 │
│  └─ Dashboard (3001)                │
└─────────────────────────────────────┘
           ↕ (Netzwerk)
┌─────────────────────────────────────┐
│  STANDRECHNER (Remote Node)         │
│  └─ Node-B (8082) ← Remote Worker  │
└─────────────────────────────────────┘
```

## Setup

### 1. Auf DIESEM Rechner (Hub):

```bash
START_HUB_WITH_NODE_A.bat
```

Startet:
- Core API / Hub (8001)
- Broker (9000)
- Node-A Worker (8081)
- WebRelay (3000)
- Dashboard (3001)

### 2. Auf STANDRECHNER (Node-B):

1. **Repository kopieren** zum Standrechner
2. **START_NODE_B.bat bearbeiten:**
   ```batch
   set HUB_IP=192.168.1.100      ← IP von DIESEM Rechner
   set BROKER_IP=192.168.1.100   ← IP von DIESEM Rechner
   ```
3. **START_NODE_B.bat ausführen**

## Konfiguration

### Hub IP ermitteln:
```powershell
ipconfig | Select-String "IPv4"
```

### Firewall-Regeln (auf Hub):
```powershell
# Port 8001 (Core API)
New-NetFirewallRule -DisplayName "Sheratan Core" -Direction Inbound -LocalPort 8001 -Protocol TCP -Action Allow

# Port 9000 (Broker)
New-NetFirewallRule -DisplayName "Sheratan Broker" -Direction Inbound -LocalPort 9000 -Protocol TCP -Action Allow
```

## Verifikation

### Auf Hub:
```bash
curl http://localhost:8001/health
curl http://localhost:9000/health
curl http://localhost:8081/health  # Node-A
```

### Auf Node-B:
```bash
curl http://localhost:8082/health  # Node-B
curl http://<HUB_IP>:8001/health   # Hub erreichbar?
```

## Troubleshooting

### Node-B kann Hub nicht erreichen:
1. Firewall-Regeln prüfen
2. Ping-Test: `ping <HUB_IP>`
3. Port-Test: `Test-NetConnection -ComputerName <HUB_IP> -Port 8001`

### Node registriert sich nicht:
1. Broker-Logs prüfen
2. Node-Logs prüfen
3. Netzwerk-Verbindung testen
