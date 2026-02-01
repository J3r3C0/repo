# REPO MAP — Sheratan (Stand: 2026-01-31)

Quelle: WORK ORDER 0001 + Klarstellungen. Fokus: Rolle, Status, empfohlene Aktion pro Repo.

## Entscheidungsregeln (Kurzfassung)

- **Source of Truth (Core)**: `sheratan-core-v2`.
- **sauber_main**: operatives Ops-/Konsolidierungs-Repo, kein Core-SoT.
- **Altstände** (v0/v1/backup/alt/2_*): `Archive` + `deprecated` + Redirect zu `sheratan-core-v2`.
- **Unklare Repos** (gemmaloop, rebug, sheratanium, Sheratan_CPU, Sheratan_edge, standalone_worker, tools, saas_tool_backlink): `Experiment` + `exploratory` + Aktion `keep isolated / evaluate`.
- **Infrastruktur-nahe Repos** (mesh, offgrid_mesh, router, sdk, dashboard, HUB): `Tool`/Plattform-Komponente, Status darf `active` sein.

| Repo | Kategorie | Kurzbeschreibung | Status | Empfohlene Aktion |
|---|---|---|---|---|
| sheratan-core | Core | Ältere Core-Basis gegenüber v2. | consolidate | Migrationspfad zu sheratan-core-v2 definieren, danach auslaufen lassen. |
| sheratan-core-v2 | Core | System-Kern und Source of Truth. | active | Weiterführen; alle Kernänderungen hier bündeln. |
| 2_sheratan_core | Archive | Alte/abgeleitete Core-Variante. | deprecated | Redirect/Consolidate → sheratan-core-v2. |
| sheratan-hub (HUB) | Tool | Hub/Orchestrierungskomponente nahe am Core. | active | Als Plattform-Komponente pflegen; klare Boundary zu Core. |
| sheratan-router-openai | Tool | Router/LLM-Bridge-Komponente. | active | Als Plattform-Komponente pflegen; Schnittstellen stabilisieren. |
| sheratan-sdk | Tool | Client/SDK zur Nutzung der Plattform. | active | Als Plattform-Komponente pflegen; Versionierung/Kompatibilität beachten. |
| sheratan-dashboard | Tool | UI/Dashboard für Ops & Monitoring. | active | Als Plattform-Komponente pflegen; an Core-APIs ausrichten. |
| sheratan-mesh | Tool | Mesh-/Worker-Infrastruktur. | active | Als Plattform-Komponente pflegen; Runtime-Interop sichern. |
| offgrid_mesh | Tool | Offgrid/Edge-Mesh-Variante. | active | Als Plattform-Komponente pflegen; Edge/Offgrid-Boundary klären. |
| sauber_main | Tool | Operatives Ops-/Konsolidierungs-Repo. | active | Als Konsolidierungszentrale pflegen; keine Kern-SoT-Änderungen. |
| sheratan-repo (repo) | Archive | Ältere Sammel-/Meta-Repo-Variante. | deprecated | Redirect/Consolidate → sheratan-core-v2. |
| projectroot | Archive | Alte Repo-Variante/Struktur. | deprecated | Redirect/Consolidate → sheratan-core-v2. |
| gemmaloop | Experiment | Exploratory/legacy Umfeld. | exploratory | Keep isolated / evaluate. |
| rebug | Experiment | Exploratory/Debug/POC-Repo. | exploratory | Keep isolated / evaluate. |
| backub-v0 | Archive | Backup/Altstand v0. | deprecated | Redirect/Consolidate → sheratan-core-v2. |
| saas_tool_backlink | Experiment | Exploratory/Produkt-POC. | exploratory | Keep isolated / evaluate. |
| sheratanium | Experiment | Exploratory/Side-Projekt. | exploratory | Keep isolated / evaluate. |
| Sheratan_v0 | Archive | Historische Version v0. | deprecated | Redirect/Consolidate → sheratan-core-v2. |
| Sheratan_v1 | Archive | Historische Version v1. | deprecated | Redirect/Consolidate → sheratan-core-v2. |
| standalone_worker | Experiment | Eigenständiger Worker-Ansatz/POC. | exploratory | Keep isolated / evaluate. |
| tools | Experiment | Diverse Werkzeuge/Utilities. | exploratory | Keep isolated / evaluate. |
| Sheratan_CPU | Experiment | CPU-optimierte Variante/POC. | exploratory | Keep isolated / evaluate. |
| Sheratan_edge | Experiment | Edge-Variante/POC. | exploratory | Keep isolated / evaluate. |
