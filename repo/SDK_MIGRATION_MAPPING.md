# SDK Migration Bundle - Script Mapping

## Sheratan-Core Script Inventory

**Current structure:**
- No `scripts/` directory (created during migration)
- No `tests/` directory (created during migration)  
- Root-level scripts: `test_sdk_integration.py`, `test_integration_sdk_router.py`, `check_core_startup.py`, etc.
- Tools: `tools/*.py` (system utilities, schema linters, integrity checks)
- WebRelay: `external/webrelay/` (worker implementation)

---

## Migration Bundle → Core Mapping

### 1. INGEST Script

**Bundle**: `scripts/ingest_draft_sdk.py`  
**Core Target**: `scripts/ingest_draft_sdk.py` (NEW)  
**Purpose**: Create Mission → Task → Job using SDK (replaces legacy ingest patterns)

**Key Changes**:
- ✅ Uses `SheratanClient` instead of `requests.post`
- ✅ Correct schemas: `{title, description, metadata}`, `{name, kind, params}`, `{payload, priority, depends_on}`
- ✅ No hardcoded URLs
- ✅ Capability routing built-in

**Usage**:
```bash
python scripts/ingest_draft_sdk.py \
  --title "Demo Mission" \
  --description "Test mission" \
  --kind read_file \
  --param path=core/main.py
```

---

### 2. Smoke/E2E Test

**Bundle**: `tests/smoke_e2e_sdk.py`  
**Core Target**: `tests/smoke_e2e_sdk.py` (NEW)  
**Purpose**: End-to-end test with job status polling

**Key Changes**:
- ✅ Uses SDK for all operations
- ✅ Polls job status until `completed`/`failed`
- ✅ Exit codes: 0=PASS, 1=WARN (worker not running), 2=FAIL

**Usage**:
```bash
python tests/smoke_e2e_sdk.py \
  --kind read_file \
  --param path=README.md \
  --wait-s 15
```

---

### 3. WebRelay Runtime Helper

**Bundle**: `webrelay/sdk_runtime_io.py`  
**Core Target**: `external/webrelay/sdk_runtime_io.py` (NEW)  
**Purpose**: LCP-wrapped result writer for WebRelay workers

**Key Changes**:
- ✅ Uses `sheratan_sdk.runtime_bridge` for atomic writes
- ✅ Uses `sheratan_sdk.lcp.wrap_lcp` for result wrapping
- ✅ Replaces manual JSON writes in WebRelay worker

**Integration**:
```python
# In WebRelay worker (e.g., external/webrelay/worker.py)
from sdk_runtime_io import write_lcp_result

# After LLM call
write_lcp_result(
    job_id="abc123",
    result={"ok": True, "output": llm_response},
    followups=[],
    output_dir="runtime/output"
)
```

---

## Existing Core Scripts (No Direct Mapping)

These scripts exist in sheratan-core but **don't have direct bundle equivalents**:

### Root-Level Test Scripts
- `test_sdk_integration.py` – SDK capability routing demo (already migrated)
- `test_integration_sdk_router.py` – Router integration test
- `check_core_startup.py` – Core startup verification

### Tools
- `tools/schema_linter.py` – Schema validation
- `tools/system_exercise.py` – System stress test
- `tools/soul_pulse.py` – Soul manifest checker
- `tools/verify_import_referential_integrity.py` – Import checker

### WebRelay
- `external/webrelay/worker.py` – Main worker loop (can integrate `sdk_runtime_io.py`)
- `external/webrelay/server.py` – WebRelay HTTP server

---

## Migration Checklist

- [x] SDK installed in sheratan-core (editable mode)
- [x] Created `scripts/` directory
- [x] Created `tests/` directory
- [x] Copied `ingest_draft_sdk.py` → `scripts/`
- [x] Copied `smoke_e2e_sdk.py` → `tests/`
- [x] Copied `sdk_runtime_io.py` → `external/webrelay/`
- [ ] Test `ingest_draft_sdk.py` with running Core
- [ ] Test `smoke_e2e_sdk.py` with running Core + Worker
- [ ] Integrate `sdk_runtime_io.py` into WebRelay worker
- [ ] Update `RUN_E2E_TESTS.bat` to use `tests/smoke_e2e_sdk.py`

---

## Patch Diff Candidates (If Needed)

If you want **patch diffs** instead of new files, here are the candidates:

### WebRelay Worker Integration
**File**: `external/webrelay/worker.py`  
**Change**: Replace manual result writing with `write_lcp_result()` from `sdk_runtime_io.py`

**Before**:
```python
# Manual JSON write
with open(f"runtime/output/{job_id}.result.json", "w") as f:
    json.dump({"ok": True, "output": result}, f)
```

**After**:
```python
from sdk_runtime_io import write_lcp_result

write_lcp_result(job_id, {"ok": True, "output": result}, followups=[])
```

---

## Next Steps

1. **Test Ingest**: `python scripts/ingest_draft_sdk.py --title "Test" --kind read_file --param path=README.md`
2. **Test Smoke**: `python tests/smoke_e2e_sdk.py --kind read_file --param path=README.md --wait-s 15`
3. **Integrate WebRelay**: Patch `external/webrelay/worker.py` to use `sdk_runtime_io.py`

---

## Status

✅ **Bundle Scripts Copied**  
✅ **Mapping Documented**  
🔄 **Next**: Run tests with live Core API
