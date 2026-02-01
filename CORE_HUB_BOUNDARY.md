# Sheratan Core / Hub Boundary Definition (v1.0)

Dieses Dokument definiert die strikten Zuständigkeitsbereiche innerhalb der Sheratan-Architektur, um die Wartbarkeit, Determinismus und Skalierbarkeit des Systems zu gewährleisten.

## 1. Sheratan Core (Der Wahrnehmungs-Kernel)
Der Core ist das „Auge“ des Systems. Er ist rein reaktiv und mathematisch.

*   **Zuständigkeit**: 
    *   Ereignis-Ingest & Zeitliche Segmentierung.
    *   Resonanz-Berechnung & Salienz-Extraktion.
    *   Identitäts-Selektion (Top-K States).
    *   Deterministische Replays.
*   **Harte Regeln**:
    *   **Keine Agentik**: Der Core darf keine Entscheidungen über Aktionen treffen.
    *   **Keine LLMs**: Der Core nutzt keine Sprachmodelle.
    *   **Determinismus**: Bei gleichem Input muss der `state_hash` identisch bleiben.
    *   **Purity**: Darf niemals Module aus dem `hub/` oder der `agency/` importieren.

## 2. Sheratan Hub (Die Agentur)
Der Hub ist das „Gehirn“ des Systems. Er orchestriert Planung und Aktion.

*   **Zuständigkeit**: 
    *   Missions- und Task-Management.
    *   Job-Dispatching & Queue-Handling.
    *   MCTS-basierte Aktionsauswahl (Agentik).
    *   Zustands-Überwachung & Scoring.
*   **Harte Regeln**:
    *   Nutzt den Core als Datenquelle, modifiziert ihn aber nicht direkt.
    *   Steuert alle externen Interaktionen über das LCP (Language Control Protocol).

## 3. Router-Layer (Abstraktion)
Kapselt die Komplexität externer Provider.

*   **Zuständigkeit**: 
    *   Anbindung an OpenAI, Anthropic, etc.
    *   Modell-spezifische Prompt-Templates.
    *   Token-Tracking & Fehlermanagement (Retries).
*   **Darf nicht**: Business-Logik oder Missions-Status verwalten.

## 4. Worker (Ausführung)
Die „Hände“ des Systems.

*   **Zuständigkeit**: 
    *   Ausführung spezifischer Jobs (Code-Patching, Analyse, Research).
    *   Kommunikation ausschließlich via LCP-Envelopes.
*   **Darf nicht**: Den globalen Missions-Status kennen oder andere Worker direkt steuern.

## 5. Anti-Patterns (Zu vermeiden)
*   **„Agentik im Core“**: Der Versuch, im Wahrnehmungs-Loop LLM-Entscheidungen zu treffen.
*   **„Direkte DB-Schreibzugriffe durch Worker“**: Worker sollten Ergebnisse immer über den Hub/Integrations-Layer zurückgeben.
*   **„Zirkuläre Abhängigkeiten“**: Core-Module, die Hub-Logik benötigen.

---
*Status: Verbindlich für alle Neuentwicklungen ab v2.9.*
*Deliverable for Work Order 0003.*
