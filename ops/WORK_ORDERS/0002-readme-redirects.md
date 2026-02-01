# WORK ORDER 0002 — README REDIRECTS & ARCHIV-KLARHEIT

## Goal
Vermeide Verwirrung durch alte Repos: **jede deprecated Codebase erklärt klar, wohin sie gehört**.

## Scope
Repos mit Überschneidung oder POC-Charakter, z. B.:

- 2_sheratan_core
- Sheratan_v0
- Sheratan_v1
- backub-v0
- alte repo/projectroot Varianten

## Task
1. Identifiziere Repos mit Status `archive` oder `deprecated`
2. Ersetze deren README durch:
   - Kurze Erklärung **warum deprecated**
   - Link zum Nachfolger (z. B. `sheratan-core-v2`)
   - Klarer Hinweis: *nicht mehr aktiv*

## Definition of Done (DoD)
- README jedes deprecated Repos enthält:
  - ⚠️ Status-Hinweis
  - 👉 Verweis auf aktives Repo
- Keine falschen Marketing-Claims mehr

## Constraints
- Kein Löschen von Code
- Keine Umstrukturierung

## Deliverable
- Geänderte READMEs in den betroffenen Repos
