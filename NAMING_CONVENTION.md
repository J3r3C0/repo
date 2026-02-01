# Sheratan Repository Naming Convention & Migration Plan

Dieses Dokument legt die verbindliche Benennungsstruktur für das Sheratan-Ökosystem fest, um Klarheit für Entwickler und Nutzer sicherzustellen.

## 1. Benennungsstruktur

| Präfix | Zweck | Beispiel |
| :--- | :--- | :--- |
| `sheratan-core-*` | Kern-Engines (Perception, Mission) | `sheratan-core`, `sheratan-core-v2` |
| `sheratan-tool-*` | Hilfs- und Analyse-Werkzeuge | `sheratan-tool-rebug` |
| `sheratan-exp-*` | Experimentelle Prototypen & Forschung | `sheratan-exp-mri`, `sheratan-exp-gemmaloop` |
| `sheratan-product-*` | Marktfähige Endprodukte / SaaS | `sheratan-product-backlink` |
| `sheratan-legacy-*` | Veralteter Code / Archivierte Versionen | `sheratan-legacy-v1`, `sheratan-legacy-poc` |
| `sheratan-meta` | Zentrale Dokumentation & Infrastruktur-Skripte | `sheratan-meta` |
| `sheratan-mesh` | Peer-to-Peer / Kommunikations-Infrastruktur | `sheratan-mesh` |
| `sheratan-sdk` | Client-Bibliotheken (Polyglot) | `sheratan-sdk` |
| `sheratan-worker` | LCP-konforme Worker-Instanzen | `sheratan-worker`, `sheratan-worker-coder` |

## 2. Migrations-Tabelle

| Aktueller Name | Zielname | Aktion | Status (Ziel) |
| :--- | :--- | :--- | :--- |
| `sheratan-core` | `sheratan-core` | **keep** | Active |
| `sheratan-core-v2` | `sheratan-core` | **consolidate** | Active |
| `sauber_main / repo` | `sheratan-meta` | **archive** | Archived |
| `2_sheratan_core` | `sheratan-legacy-poc` | **archive** | Archived |
| `Sheratan_v0 / v1` | `sheratan-legacy-v0 / v1` | **rename/archive** | Legacy |
| `sheratan-sdk` | `sheratan-sdk` | **keep** | Active |
| `HUB / sheratan_hub` | `sheratan-hub` | **rename** | Active |
| `sheratan-dashboard` | `sheratan-dashboard` | **keep** | Active |
| `standalone_worker` | `sheratan-worker` | **rename** | Active |
| `rebug` | `sheratan-tool-rebug` | **rename** | Active |
| `gemmaloop` | `sheratan-exp-gemmaloop` | **rename** | Experiment |
| `offgrid_mesh` | `sheratan-mesh` | **consolidate** | Active |
| `projectroot` | `sheratan-meta` | **consolidate** | Active |
| `backub-v0` | `sheratan-backup` | **rename** | Backup |

---
*Deliverable for Work Order 0004.*
