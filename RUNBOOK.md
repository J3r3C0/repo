# Sheratan Business & Operations Runbook (v1.0)

Dieses Dokument dient als Einstiegspunkt für den Betrieb und das Verständnis des Sheratan-Ökosystems. Es konzentriert sich auf den stabilen Ist-Zustand für Partner und Investoren.

## 1. Was ist Sheratan?
Sheratan ist ein modulares Multi-Agent-System, das eine Brücke zwischen deterministischer Datenverarbeitung und agiler KI-Orchestrierung schlägt. Es ermöglicht Unternehmen, autonome Missionen in einer kontrollierten, auditierbaren Umgebung auszuführen, wobei die Wahrnehmung (Perception) strikt von der Entscheidungskontrolle (Hub) getrennt bleibt.

## 2. Produktionstaugliche Komponenten
Die folgenden Module bilden den stabilen Kern des Systems:

| Komponente | Rolle | Status |
| :--- | :--- | :--- |
| **Sheratan Core** | Deterministischer Wahrnehmungs-Kernel. | Produktion (v1) |
| **Sheratan Hub** | Missions-Kontrolle & Agenten-Orchestrierung. | Produktion (v2) |
| **Sheratan SDK** | Programmierschnittstellen (Python/TS). | Aktiv |
| **Sheratan Dashboard** | Echtzeit-Monitoring & Missions-Steuerung. | Aktiv |

## 3. Minimal-Start-Sequenz
Um ein funktionsfähiges Sheratan-Umfeld lokal zu starten, folgen Sie dieser Reihenfolge:

1.  **Start Core Perception API**: 
    - Führen Sie `START_CORE_ONLY.bat` im `sheratan-core` Verzeichnis aus.
    - Port: **8005**
2.  **Start Mission Hub & Orchestra**: 
    - Führen Sie `START_HUB_WITH_NODE_A.bat` im `sheratan-core` Verzeichnis aus.
    - Port: **8001**
3.  **Start Dashboard**: 
    - Führen Sie `npm run dev` im `sheratan-dashboard` Verzeichnis aus.
    - Web-UI: `http://localhost:5173` (typisch für Vite)

## 4. System-Health Check
Das System gilt als „gesund“, wenn:
- `/api/health` auf den Ports 8001 und 8005 einen `200 OK` Status liefert.
- Der `state_hash` im Core bei identischen Eingangsdaten invariant bleibt.
- Das Dashboard eine Verbindung zum Hub herstellen kann (Grüner Status-Indikator).

## 5. Abgrenzung (Non-Scope)
Die folgenden Bereiche sind aktuell **Forschung oder Experimente** und nicht Teil des stabilen Standard-Runbooks:
- GPU-beschleunigter Bit-perfekter Determinismus (in Entwicklung).
- Experimentelle Module wie `gemmaloop` oder `mri-mechanistics`.
- Hardware-spezifische Edge-Optimierungen (`Sheratan_edge`).

---
*Status: Operations-Ready. Erstellt für Work Order 0005.*
