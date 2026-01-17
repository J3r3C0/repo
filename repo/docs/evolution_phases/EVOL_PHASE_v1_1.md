# Evolution Phase: v1.1 – Measurement Hardening

**Base Version:** Sheratan Evolution v1
**Status:** ACTIVE
**Intent:** Stabilize measurement and verification without changing functional semantics.

## 🎯 Goals
- Harden **SystemExercise** against environmental edge cases (timeouts, port collisions).
- Refine **Import-Trace** precision (filter out platform-specific noise).
- Establish **Size-Report** historical tracking (compare against `manifest_baseline.json`).

## ✅ Explicitly Allowed
- Improvements to reporting tools (`tools/size_report.py`, `tools/import_trace.py`).
- Additions to `system_exercise.py` (new checks for existing features).
- Documentation updates (Readmes, DoD).
- Fixes for packaging/build stability.

## ❌ Explicitly Forbidden
- Adding new **Job Kinds**.
- Modifying **Core API** signatures or behavior.
- Changes to **Policy/Routing** logic.
- Adding non-optional heavy dependencies.

## 🏁 Definition of Success
- `SystemExercise` runs reliably in CI and locally across Windows environments.
- All reports (`exercise`, `feature`, `import`, `size`) are generated and stable.
- Zero regressions in the core functional surface.

---
*Locked under Sheratan Evolution v1 Governance.*
