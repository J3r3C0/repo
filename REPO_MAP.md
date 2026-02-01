# Sheratan Repository Map (Work Order 0001)

This document provides a comprehensive overview of all Sheratan repositories, their roles, current status, and recommended actions.

| Repo | Kategorie | Kurzbeschreibung | Status | Empfohlene Aktion |
| :--- | :--- | :--- | :--- | :--- |
| **sheratan-core** | Perception | Deterministische Segment-Engine; extrahiert Salienz und wählt Identitäten. | active | Behalten (v1 Stable) |
| **sheratan-core-v2** | Mission-Core | FastAPI-Server für Missionen, Tasks und Jobs mit LCP-Worker-Integration. | active | Haupt-Core für v2 Entwicklung |
| **sheratan-router-openai** | Router | Routing für OpenAI-basierte LLM-Aufrufe, Provider-Abstraktion. | active | Behalten |
| **sheratan-sdk** | SDK | Python- & TypeScript-Client für LLM-Jobs und HMAC-Signaturen. | active | Behalten |
| **sheratan-dashboard** | Dashboard | React/Vite-Dashboard zur Visualisierung und Steuerung. | active | Behalten |
| **HUB / sheratan_hub** | Hub | Agenten-/Modul-Orchestrierung, zentrale Steuerung. | active | Repositories in `sheratan-hub` zusammenführen |
| **sheratan-mesh / offgrid_mesh** | Mesh | Dezentrale Kommunikationsschicht, Off-Grid-Netzwerk. | active | Repositories konsolidieren |
| **standalone_worker** | Worker | LCP-Worker für Queue-Abarbeitung (Analyse, Code-Rewrite). | active | In `sheratan-worker` umbenennen |
| **sauber_main / repo** | Core (v2.9) | Beschreibt stabile Engine mit Fokus auf Sicherheit. | archive | Dokumentation in `sheratan-core-v2` integrieren |
| **2_sheratan_core** | Mission-Core (POC) | Proof-of-Concept mit Docker-Stacks und LCP-Konzept. | archive | Inhalte in `sheratan-core-v2` integrieren |
| **rebug** | Tools | Debugging-Tool für deterministische Replays. | active | In `sheratan-meta` oder eigenes Tool-Repo konsolidieren |
| **projectroot / sheratan-repo** | Meta | Sammel-Repositories und Skripte. | consolidate | In `sheratan-meta` zusammenführen |
| **tools / backub-v0** | Tools | Hilfsprogramme und Sicherungen. | consolidate | In `sheratan-meta` / `sheratan-backup` überführen |
| **gemmaloop / mechanistic_mri** | Experiment | Forschungs- und Prototypenprojekte. | experiment | Als `sheratan-exp-*` kennzeichnen |
| **Sheratan_CPU / Sheratan_edge** | Hardware/Edge | Vorläufige Hardware-/Edge-Projekte. | experiment | Dokumentation schärfen |
| **Sheratan_v0 / Sheratan_v1** | Legacy | RAG/ETL-Monorepo / Nachfolger. | legacy | Archivieren oder zu `sheratan-rag` umbenennen |
| **saas_tool_backlink** | Product | Vertikales SaaS-Tool. | active | Nur bei konkretem Use-Case weiterführen |
| **sheratanium** | Product | Marken- und Plattformkonzept. | concept | Behalten |

---
*Created per Work Order 0001 instructions based on Master README sources.*
