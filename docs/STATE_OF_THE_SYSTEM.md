# State of the System (Jan 2026)

Dieses Dokument definiert den aktuellen Referenzrahmen der Sheratan-Architektur. Es dient als "Single Source of Truth", um Inkonsistenzen in der Interpretation des System-Zustands zu vermeiden.

## 1. Was ist Sheratan heute?
Sheratan ist ein modulares Ökosystem für dezentrale, deterministische Wahrnehmung und agentiale Orchestrierung. Es ist kein monolithisches Produkt, sondern eine komponentenbasierte Architektur.

## 2. Stabile Komponenten (Tier 1)
Die folgenden Komponenten sind architektonisch gesetzt und bilden die Basis für den produktiven Einsatz:
- **Perception Kernel (Core)**: Deterministische State-Engine (Port 8005).
- **Mission Hub**: API für Missions- und Job-Verwaltung (Port 8001).
- **LCP (Language Control Protocol)**: Standard für agentialen Datenaustausch.
- **SDK**: Tools für HMAC-signierte Kommunikation.

## 3. Explorative Komponenten (Tier 2/3)
Diese Module sind funktional, befinden sich aber in stetiger Evolution:
- **Mesh/Offgrid**: Dezentrale Kommunikationsschichten.
- **MCTS Action Selection**: Integration in den Hub zur autonomen Planung.
- **Dashboard**: Visualisierungs-Layer (Work in Progress).

## 4. Bewusst ausgenommen (Non-Scope)
Aktivitäten in diesen Bereichen gelten als experimentell und sind nicht Teil des stabilen Kern-Anspruchs:
- Integrierte LLM-Modelle (Sheratan nutzt externe Router).
- Vollständige GPU-Bit-Perfektion (Fokus liegt auf CPU-Determinismus).
- Veraltete POCs (2_sheratan_core, etc.).

## 5. Leit-Dokumente
Für detaillierte Entscheidungen gelten folgende Policies:
1. [REPO_MAP.md](../REPO_MAP.md) - Status und Rolle jedes Repositories.
2. [CORE_HUB_BOUNDARY.md](../CORE_HUB_BOUNDARY.md) - Strikte Trennung Perception vs. Action.
3. [NAMING_CONVENTION.md](../NAMING_CONVENTION.md) - Zukünftige Strukturvorgabe.
4. [RUNBOOK.md](../RUNBOOK.md) - Operativer Leitfaden.

---
*Referenz: sheratan-state-2026-01*
