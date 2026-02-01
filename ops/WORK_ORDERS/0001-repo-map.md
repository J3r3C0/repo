# WORK ORDER 0001 — REPO MAP & STATUS KLARHEIT

## Goal
Erzeuge eine **vollständige, aktuelle Übersicht aller Sheratan-Repos** mit klarer Rolle, Status und empfohlener Aktion.

## Scope
GitHub-Repos (alle freigegebenen):

- sheratan-core
- sheratan-core-v2
- 2_sheratan_core
- sheratan-hub / HUB
- sheratan-router-openai
- sheratan-sdk
- sheratan-dashboard
- sheratan-mesh
- offgrid_mesh
- sauber_main
- sheratan-repo / repo
- projectroot
- gemmaloop
- rebug
- backub-v0
- saas_tool_backlink
- sheratanium
- Sheratan_v0 / Sheratan_v1
- standalone_worker / tools / Sheratan_CPU / Sheratan_edge

## Task
1. Analysiere pro Repo:
   - Zweck / Rolle
   - Nähe zu **KERN / TOOL / PRODUKT**
   - Reifegrad
2. Erstelle eine Tabelle `REPO_MAP.md` mit Spalten:
   - Repo
   - Kategorie (Core / Tool / Experiment / Product / Archive)
   - Kurzbeschreibung (1 Satz)
   - Status (`active | consolidate | archive | deprecated`)
   - Empfohlene Aktion

## Definition of Done (DoD)
- Datei `REPO_MAP.md` existiert
- Alle bekannten Repos sind enthalten
- Jede Zeile hat **eine klare Entscheidung**

## Constraints
- Keine Code-Änderungen
- Nur Analyse & Dokumentation

## Deliverable
- `REPO_MAP.md`
