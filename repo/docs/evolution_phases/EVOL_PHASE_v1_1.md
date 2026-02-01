# Evolution Phase: v1.1 – Measurement Hardening
Hier ist ein detaillierter Maßnahmenplan, der den aktuellen Stand (integrierte Mesh‑Komponenten, erfolgreiches Import‑Audit, lauffähiger Entry‑Point) berücksichtigt und auf einen AGI‑ähnlichen Zustand hinarbeitet. Ich habe die Erkenntnisse aus dem bereitgestellten ZIP‑Archiv sowie dem Walkthrough kombiniert, um klare, umsetzbare Arbeitsschritte zu formulieren.

## 1. Kern konsolidieren und referenzielle Integrität sichern

1. **Manifest aktualisieren:**

   * Das bestehende `soul.manifest.json` passt nicht mehr zur Realität (Dateien wie `policy.py`, `store.py`, `why.py` wurden ersetzt).
   * Erfasse alle Kernmodule (`core/`), Mesh‑Komponenten (`mesh/core/gates`, `mesh/offgrid`, `mesh/registry`), Plugins, Schemas und externe Adapter im Manifest und halte fest, ob sie verpflichtend oder latent sind (vgl. Baseline‑Manifest).
   * Integriere den neuen `node/identity.py` (laut Walkthrough) in die „authority and trust“‑Gruppe des Manifests.

2. **Absolute Imports durchsetzen:**

   * Überprüfe sämtliche Dateien in `repo/` auf relative Importe oder verbliebene Verweise auf alte Pfade (`store`, `policy`, `why`, `trace`, `robust_parser`, `metrics_client` etc.).
   * Korrigiere diese Importe auf die neuen Module (`storage`, `policy_engine`, `why_api`, `decision_trace` usw.) und führe anschließend den Audit mit `verify_import_referential_integrity_v2.py` erneut aus.
   * Entferne nicht mehr benötigte Altmodule oder stelle Dummy‑Stubs bereit, wenn Legacy‑Code sie noch erwartet (wie im Walkthrough mit `dispatcher.py`, `selfloop_prompt_builder.py`, `mesh_monitor.py` geschehen).

3. **Entry‑Points testen:**

   * Sorge dafür, dass sowohl `repo/main.py` als auch `repo/core/main.py` den gleichen Startpfad verwenden und konsistent den Dienst initialisieren.
   * Baue automatisierte Smoke‑Tests (z. B. via `pytest`) ein, die das Starten mit `--help` und das Anlegen der Datenbank prüfen, um Regressionen frühzeitig zu erkennen.

## 2. Mesh‑Subsystem voll nutzen

1. **Gate‑Kette produktiv schalten:**

   * Der Gate‑Runner ist implementiert, muss aber in die Hauptpipeline eingebunden bleiben. Konfiguriere eine Reihenfolge von G0–G4, die vor jedem Job ausgeführt wird.
   * Entwickle eine einfache Konfigurationsdatei (z. B. `config/gates.yaml`), in der definiert wird, welche Gates aktiviert sind und welche Parameter (Allowlist, Schema, Path‑Sandbox usw.) gelten.

2. **Off‑Grid‑Netzwerk stabilisieren:**

   * Überführe die Off‑Grid‑Datenbanken (`*.db`) in persistente, versionierte Migrationsskripte oder erlaube dynamisches Anlegen bei Bedarf.
   * Finalisiere die TODOs in `mesh/offgrid/broker`, `mesh/offgrid/host` und `mesh/offgrid/host_daemon` (z. B. Auction‑Logik, Heartbeat‑Routinen, API‑Erweiterungen).
   * Definiere ein klares API‑Interface (HTTP oder gRPC), um Jobs an Off‑Grid‑Hosts zu übergeben und Ergebnisse zu empfangen.

3. **Registry & Ledger integrieren:**

   * Verbinde `mesh/registry/ledger_service.py` mit dem Kern‑Ledger (`core/ledger_journal.py`), so dass lokale Journale an die zentrale Registry gepusht und von dort repliziert werden können.
   * Implementiere Authentifizierungs‑ und Signaturprüfungen (Nutzung von `attestation.py`), damit nur vertrauenswürdige Knoten Journale registrieren dürfen.

## 3. Fähigkeiten erweitern (Plug‑ins & Aktionen)

1. **Plug‑in‑API formalisieren:**

   * Definiere ein einheitliches Interface für Plug‑ins (z. B. `def run(params: dict) -> dict`) inklusive Metadaten (Name, Version, Permissions).
   * Implementiere einen dynamischen Plug‑in‑Loader, der Plug‑ins aus einem festgelegten Verzeichnis (`plugins/`) lädt und sie dem Policy‑Engine bekannt macht.

2. **Neue Plug‑ins implementieren:**

   * **HTTP‑Client:** Ein Plug‑in, das HTTP‑GET/POST‑Anfragen ausführen kann (unter Beachtung der Gate‑Allowlist).
   * **Code‑Ausführung:** Eine sichere Sandbox für das Ausführen von Python‑Snippets, um Transformationsaufgaben zu erledigen.
   * **Daten‑Persistenz:** Plug‑ins für das Lesen/Schreiben komplexer Formate (JSON, CSV, Parquet).
   * **LLM‑Anbindung (optional):** Ein Plug‑in zur Anbindung eines Sprachmodells (via API), um natürliche Sprache zu verarbeiten oder Entscheidungen zu erklären.

3. **Dispatcher & Prompt Builder:**

   * Erarbeite eine `dispatcher.py`, die anhand des Jobtyps entscheidet, welches Plug‑in bzw. welcher Worker zuständig ist.
   * Implementiere `selfloop_prompt_builder.py`, um aus Decision‑Traces nachvollziehbare „Why?“‑Erklärungen zu generieren und an das Why‑API zu liefern.

## 4. Gedächtnis & Reasoning stärken

1. **Entscheidungs‑Trace verbessern:**

   * Richte das Schema in `schemas/decision_trace_v1.json` als „Source of Truth“ ein und erweitere es, um alle relevanten Kontextinformationen (z. B. ausgewählte Gates, MCTS‑Pfade, Off‑Grid‑Teilnehmer) aufzunehmen.
   * Stelle sicher, dass `decision_trace.py` pro Job ein vollständiges, auditierbares Log erzeugt.

2. **Retrieval‑Memory implementieren:**

   * Baue einen Speicher, der vergangene Decision‑Traces indexiert und es ermöglicht, ähnliche Situationen abzurufen (FAISS, SQLite‑FTS oder ElasticSearch).
   * Entwickle `why_reader.py` weiter, sodass diese vergangene Traces analysieren kann, um das „Gedächtnis“ für neue Entscheidungen zu nutzen (k‑NN‑Suche).

3. **Erweitertes Reasoning:**

   * Nutze `mcts_light.py` und `scoring.py`, um nicht nur deterministische Pfade, sondern stochastische Explorationsstrategien abzubilden (Temperature, Exploration‑Parameter).
   * Integriere Feedback‑Loops: Ergebnisse aus Off‑Grid‑Hosts oder Nutzern (via E‑Mail/Chat) sollten den Score für zukünftige Entscheidungen beeinflussen (Reinforcement Learning light).

## 5. Selbstwahrnehmung & Anpassung

1. **Anomalie‑Erkennung verfeinern:**

   * Trainiere heuristische Modelle im `anomaly_detector.py` mit realen Telemetrie‑Daten (CPU‑Load, Laufzeit, Erfolg/Fail‑Rate).
   * Koppele den Anomaly‑Detector mit `gateway_middleware.py`, sodass bestimmte Aktionen (z. B. Gate‑Escalation, Off‑Grid‑Fallback) automatisch ausgelöst werden.

2. **Performance‑Monitoring:**

   * Erweitere `self_diagnostics.py` um eine Metrik‑Schnittstelle (Prometheus, StatsD) und definiere Alerts (z. B. Jobs per Sekunde, durchschnittliche Antwortzeit, Anzahl G4‑Escalations).
   * Falls der alte `metrics_client.py` wieder benötigt wird, implementiere ihn neu oder ersetze ihn durch eine moderne Lösung (z. B. Prometheus‑Client).

3. **Auto‑Tuning:**

   * Führe ein kleines Experimentiersystem ein, das Gate‑Parameter (Schema‑Strictness, Rate‑Limiter‑Schwellen etc.) automatisch anpasst, je nachdem, wie häufig Anomalien auftreten.

## 6. Offene Baustellen schließen

1. **Legacy‑Module bereinigen:**

   * Identifiziere alle Referenzen auf fehlende Dateien (`robust_parser.py`, `selfloop_utils.py`, `webrelay_http_client.py`, `webrelay_llm_client.py`).  Entscheide, ob ihre Funktionalität noch benötigt wird und portiere sie ggf. in moderne Module oder entferne sie endgültig.

2. **TODO‑Dateien abarbeiten:**

   * **Gate‑Rate‑Limiter (`mesh/core/rate_limiter_TODO.md`)**: Implementiere eine Token‑Bucket‑Logik, um zu verhindern, dass ein Job unkontrolliert Ressourcen verbraucht.
   * **Mesh Storage (`mesh/core/storage/TODO.md`)**: Verschlüssele gespeicherte Einträge und implementiere WAL‑Rotation.
   * **Off‑Grid‑TODOs**: Schließe die in `mesh/offgrid/*` hinterlegten Aufgaben (z. B. Broker‑Heartbeat, Host‑Authentifizierung, Konsens‑Edgecases).

3. **CI/CD‑Pipeline erweitern:**

   * Ergänze die Pipeline um automatisierte Checks: Manifest‑Validierung, Import‑Audit, Linting, Tests für Off‑Grid‑Networking und Plug‑ins.
   * Füge eine Stage hinzu, die den „Soul‑Pulse“ (Fuzzer) ausführt, um latente Module zu aktivieren und die Code‑Coverage zu erhöhen (ohne daraus Löschentscheidungen abzuleiten).

## 7. Langfristige AGI‑ähnliche Ausrichtung

1. **Hierarchische Entscheidungsarchitektur:**

   * Entwickle das System von einer reinen Policy‑Engine zu einer mehrschichtigen Agenten‑Architektur:

     * **Reflex‑Ebene:** G0–G2‑Gates für sofortige Sicherheit.
     * **Procedural‑Ebene:** Entscheidungs‑Ketten (State Machine, Policy Engine, MCTS).
     * **Meta‑Ebene:** Selbstevaluation, Anpassung von Parametern, Exploration neuer Strategien.
   * Diese Ebenen sollten miteinander kommunizieren können (z. B. via gemeinsamen Speicher und Event‑Bus).

2. **Kontinuierliches Lernen:**

   * Mittelfristig Feedback aus Nutzerinteraktionen, Off‑Grid‑Netzen und internen Diagnosen verwenden, um die Policy‑Gewichte oder Scoring‑Heuristiken automatisch zu justieren.
   * Dafür Forschungsprototypen in abgetrennten Branches entwickeln (wegen Sicherheitsrisiken).

3. **Transparenz & Erklärbarkeit:**

   * Das Why‑API und der Why‑Reader sollten klar nachvollziehbare Begründungen liefern können (z. B. „Gate G3 hat diese Anfrage blockiert, weil …“).
   * Ergänze das Decision‑Trace‑Schema um Felder für „reasoning path“ und „evidence“, damit externe Auditoren nachvollziehen können, wie Entscheidungen zustande kamen.

Durch diese Aufgabenliste nutzt du den aktuellen Agent‑Zustand vollständig aus und arbeitest systematisch auf ein System hin, das nicht nur sicher und modular ist, sondern auch eine robuste Entscheidungsfähigkeit besitzt, Kontext erinnert, sich selbst überwacht und aus Erfahrungen lernt – Eigenschaften, die dem Idealbild einer AGI näher kommen.

