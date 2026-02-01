<<<<<<< HEAD
# ⚠️ ARCHIVED / DEPRECATED — Sauber Main / Repo
=======
<<<<<<< HEAD
${analyze_phase10_coverage.updated_readme}
=======
# Sheratan Core
>>>>>>> dac0dd84bdb11798c2456fd7f5585feec03322f7

Dieses Repository ist **nicht mehr aktiv** und dient nur noch Archivzwecken. Es enthält den historischen Stand v0.3.0 der Sheratan-Engine.

👉 Der aktuelle Sheratan-Core (v2) befindet sich hier: **[sheratan-core](file:///c:/neuer%20ordner%20f%C3%BCr%20allgemein%20github%20pulls/sheratan-core)**

### Warum?
Die stabilen Komponenten aus `sauber_main` und `repo` wurden im Rahmen der v2.9-Migration in das zentrale `sheratan-core` Repository überführt.

---
<<<<<<< HEAD
*Bitte nutze ab sofort das aktive Repository `sheratan-core` für alle neuen Entwicklungen.*
=======

## Project Status

🟢 Track B (Reliability) completed  
Acceptance Gate passed. Tags finalized (`track-b2-complete`, `track-b3-complete`, `v0.3.0`).  
System is deployment-ready.

---

## Executive Summary

Sheratan Core has successfully passed all production readiness and stability gates. It is a reliable, manipulation-resistant system designed for production environments. With v0.3.0, it includes a full observability suite and standalone distribution capabilities.

### Core Values
- **Reliability**: Remains stable under load, detects duplicate/faulty requests, and ensures consistent results.
- **Security**: Cryptographic identity for all components, automated drift/spoof detection, and controlled security enforcement.
- **Transparency**: Fully auditable system state, automated metric tracking, and explainable decision traces.

---

## Technical Capabilities (Sheratan v0.3.0)

### 🛡️ Governance & Security (Track A)
- **Node Identity (A4)**: Ed25519 identity with TOFU-pinning and signed heartbeats.
- **Node Attestation (A2)**: Automated signal tracking for build-id, capability hash, and runtime drift.
- **Enforcement Layer (A3)**: Graduated response (WARN/QUARANTINE) based on attestation health.
- **Token Rotation (A1)**: Zero-downtime credential rotation.

### ⚡ Data-Plane Robustness (Track B)
- **Result Integrity (B3)**: Canonical SHA256 hashing for all results. Tamper detection triggers 403 Forbidden and audit alerts.
- **Idempotency (B2)**: At-most-once semantics with gateway hashing and collision detection.
- **Backpressure (B1)**: Queue-depth limits, inflight-limits, and DB-native lease management.

### 📊 Observability & Operations (Track C)
- **Ops/NOC Dashboard**: Real-time monitoring of health, queue depth, and SLO violations.
- **Alert Center**: Automated detection of stalls, bursts, and integrity failures.
- **Diagnostic Bundler**: One-click system state snapshots and log collection (sanitized).
- **Service Mesh Metrics**: Live visibility into node health and performance.

### 🚀 Distribution (Track D)
- **Standalone EXE**: One-file distribution for Windows (Core + Assets).
- **Embedded UI**: React dashboard served directly via Port 8001 `/ui`.
- **Persistent Storage**: Robust separation of read-only assets and writable data.

---

## Proof of Work & Verification

The system state is continuously validated via the **Sheratan Acceptance Suite**:
- `scripts/acceptance.ps1` -> **PASS**
- `verify_b2_idempotency.ps1` -> **PASS**
- `verify_b3_result_integrity.ps1` -> **PASS**

---

## Getting Started

### Quick Launch (EXE)
If you have the bundled version:
```powershell
.\sheratan_core.exe
```
The dashboard is then available at `http://localhost:8001/ui/`.

### Development Launch
```powershell
.\START_COMPLETE_SYSTEM.bat
```

### Verification
To run the full production acceptance gate:
```powershell
.\scripts\acceptance.ps1
```

---

## Documentation
- [System Overview](docs/system_overview.md) - Port guide and architecture.
- [Architecture](docs/SHERATAN_REFACTORING_PLAN.md) - Technical design.
- [Observability Guide](docs/Track%20C%20Observability.md) - Monitoring and Alerts.

---
**Status**: Sheratan v0.3.0 Milestone reached. Deployment Ready.
>>>>>>> 93326358f2ba9d1c50676c4bdc21e429abaeb1ec
>>>>>>> dac0dd84bdb11798c2456fd7f5585feec03322f7
