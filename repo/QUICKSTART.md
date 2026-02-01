# Sheratan Quick Start

**Ziel**: System in 5 Minuten zum Laufen bringen.

---

## 1. Installation (Einmalig)

Falls das System frisch geklont wurde oder Abhängigkeiten fehlen:

```cmd
SETUP.bat
```

**Was passiert:**
- Installiert Python Dependencies
- Installiert Node.js Module (Dashboard & WebRelay)
- Baut das Dashboard (`npm run build`)
- Erstellt eine initiale `.env` Datei

---

## 2. System starten

```cmd
START_COMPLETE_SYSTEM.bat
```

**Was passiert:**
- 6 Services starten in separaten Fenstern
- **Warm-up**: Das System wartet 15 Sekunden auf die Stabilisierung
- Dashboard öffnet automatisch unter `http://localhost:3001`

---

## 3. Erfolgskontrolle

Öffne das Dashboard: `http://localhost:3001`

**Erwartung:**
- ✅ **Mesh Nodes**: 2/2 online (Host-A, Host-B)
- ✅ **System State**: OPERATIONAL (nach Warm-up)
- ✅ **Core API**: Verbunden (Port 8001)

---


## 3. System testen

### Option A: Über Dashboard
1. Öffne Dashboard
2. Klicke "Create Mission"
3. Fülle Formular aus
4. Beobachte Job-Ausführung

### Option B: Über API
```powershell
# Mission erstellen
$mission = @{
    title = "Test Mission"
    description = "Erste Test-Mission"
    priority = "normal"
} | ConvertTo-Json

Invoke-RestMethod -Method Post `
    -Uri http://localhost:8001/api/missions `
    -Body $mission `
    -ContentType "application/json"

# Jobs anzeigen
Invoke-RestMethod http://localhost:8001/api/jobs
```

---

## 4. System-Health prüfen

```powershell
# System State
Invoke-RestMethod http://localhost:8001/api/system/state

# Alle Services testen
$ports = @(8001, 9000, 3000, 3001, 8081, 8082)
foreach ($p in $ports) {
    try {
        Invoke-WebRequest "http://localhost:$p" -TimeoutSec 1 -UseBasicParsing | Out-Null
        Write-Host "✅ Port $p - OK" -ForegroundColor Green
    } catch {
        Write-Host "❌ Port $p - DOWN" -ForegroundColor Red
    }
}
```

---

## 5. System stoppen

```cmd
STOP_SHERATAN.bat
```

Oder: Alle CMD-Fenster schließen.

---

## 🚨 Troubleshooting

### "Port already in use"
```cmd
STOP_SHERATAN.bat
timeout /t 5
START_COMPLETE_SYSTEM.bat
```

### "Core API not responding"
**Lösung**: Warte 60 Sekunden nach Start - Services brauchen Zeit zum Hochfahren.

### "Dashboard zeigt keine Hosts"
**Prüfen**:
1. Broker läuft: `http://localhost:9000/status`
2. Hosts laufen: `http://localhost:8081/status`, `http://localhost:8082/status`
3. Core API Logs: `logs/` Verzeichnis

### "WebRelay errors"
**Prüfen**:
1. Chrome läuft (Port 9222)
2. ChatGPT-Tab ist offen
3. WebRelay Logs im Terminal

---

## 📖 Weiterführende Dokumentation

- **[README.md](README.md)** - System-Übersicht & Doku-Links
- **[system_overview.md](docs/system_overview.md)** - Alle Ports & API-Endpoints
- **[PHASE_A_STATE_MACHINE.md](docs/PHASE_A_STATE_MACHINE.md)** - State Machine Details

---

## 🎯 Nächste Schritte

1. ✅ System läuft
2. ⏳ Erste Mission erstellen
3. ⏳ Job-Flow beobachten
4. ⏳ Logs verstehen

---

## 🚀 Sheratan Evolution (Modular Core)

Das System wurde auf eine modulare Struktur umgestellt. 
- **Core Logic**: Befindet sich nun in `core/`.
- **API Entrypoint**: `core/main.py`.
- **Mesh & Hub Components**: Befinden sich nun in `hub/`.
- **Daten & Logs**: Konsolidiert in `data/` und `logs/`.

Entwickler sollten für neue Features primär im `repo/` Verzeichnis arbeiten. Siehe [task.md](task.md) für den Migrationsstatus.
