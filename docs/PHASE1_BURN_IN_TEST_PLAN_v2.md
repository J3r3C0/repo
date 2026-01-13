# Phase 1: Burn-In Test Plan v2

**Date:** 2026-01-13  
**Priority:** P0 → P1 → P2 → P3 → P4  
**Goal:** Validate Phase 1 stability under real-world conditions

---

## Test Philosophy

**Not just smoke tests** – we need:
- ✅ Burst performance (done)
- 🔄 Long-term stability (hours/days)
- 💥 Chaos resilience (crashes, network failures)
- 🔒 Concurrency safety (locks, claiming)
- 📁 Filesystem edge cases (partial writes, watchdog storms)

---

## P0 – Immediate Fixes (10-20 min) 🔴

### 0.1 Worker Process Detection

**Problem:** `burn_in_test.ps1` shows "Worker: Cannot confirm"

**Fix:**
```powershell
# Better worker detection
$workerProcess = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -like "*worker_loop.py*"
}
```

**Test:**
```powershell
# Run and verify
.\scripts\test_p0_worker_detection.ps1
```

**Pass Criteria:**
- ✅ Worker PID found reliably
- ✅ Worker logs show heartbeat every 30s
- ✅ CPU and memory usage visible

---

### 0.2 State Machine Display Fix

**Problem:** `current_state` and `last_transition_id` show empty

**Test:**
```powershell
# Trigger transitions
curl -X POST http://localhost:8001/api/system/state/transition `
     -H "Content-Type: application/json" `
     -d '{"next_state": "RUNNING", "reason": "Test"}'

# Check state
curl http://localhost:8001/api/system/state | ConvertFrom-Json
```

**Pass Criteria:**
- ✅ `current_state` matches last transition
- ✅ `transition_id` increments correctly
- ✅ `state_transitions.jsonl` appends properly

---

## P1 – Restart Safety (30-60 min) 🟡

### 1.1 Worker Kill During Job Burst

**Scenario:** Worker crashes mid-processing

**Script:** `test_p1_worker_kill.ps1`

```powershell
# Submit 50 jobs
for ($i=1; $i -le 50; $i++) {
    # Create job...
    Start-Sleep -Milliseconds 50
}

# Kill worker after ~10 jobs
Start-Sleep -Seconds 2
Stop-Process -Name python -Force

# Restart worker
Start-Sleep -Seconds 2
cd worker
python worker_loop.py

# Wait for completion
Start-Sleep -Seconds 30

# Verify
```

**Pass Criteria:**
- ✅ All 50 jobs completed exactly once
- ✅ No permanent `.claimed` files
- ✅ No state corruption
- ✅ No lost jobs

---

### 1.2 Core Kill During HTTP Notify

**Scenario:** Core API unavailable during job completion

**Script:** `test_p1_core_kill.ps1`

```powershell
# Start jobs
# Kill Core API mid-processing
# Restart Core
# Verify recovery
```

**Pass Criteria:**
- ✅ Worker doesn't block permanently
- ✅ `failed_reports/` contains failed notifications
- ✅ Jobs complete and write results
- ✅ After Core restart, system recovers

---

### 1.3 Power Loss Simulation

**Scenario:** Ungraceful shutdown (Force-Kill all)

**Script:** `test_p1_power_loss.ps1`

```powershell
# Start system with active jobs
# Force-Kill all processes
# Restart system
# Verify recovery
```

**Pass Criteria:**
- ✅ No JSON corruption
- ✅ State machine loads last valid state
- ✅ Unclaimed jobs picked up
- ✅ No duplicate processing

---

## P2 – Concurrency & Lock Contention (60-90 min) 🟡

### 2.1 Multi-Worker Concurrency Test

**Scenario:** 2 workers, same job directory

**Script:** `test_p2_multi_worker.ps1`

```powershell
# Start 2 worker instances
# Submit 200 jobs
# Monitor claiming distribution
# Verify no duplicates
```

**Pass Criteria:**
- ✅ 0 duplicate processing
- ✅ Jobs distributed across workers
- ✅ CPU stable, no lock storms
- ✅ All jobs complete

---

### 2.2 Lock Timeout Stress Test

**Scenario:** High-frequency state transitions

**Script:** `test_p2_lock_stress.ps1`

```powershell
# Trigger 500 rapid transitions
for ($i=1; $i -le 500; $i++) {
    # Transition PAUSED ↔ RUNNING
    Start-Sleep -Milliseconds 10
}
```

**Pass Criteria:**
- ✅ Lock timeout rate <5%
- ✅ No JSON corruption
- ✅ All transitions logged

---

## P3 – Filesystem Edge Cases (30-60 min) 🟢

### 3.1 Partial Write Simulation

**Scenario:** Job file written in stages

**Script:** `test_p3_partial_write.ps1`

```powershell
# Create empty file
# Write half JSON
# Wait 500ms
# Complete JSON
# Verify worker waits for stability
```

**Pass Criteria:**
- ✅ Worker waits for file stability
- ✅ No JSON parse errors
- ✅ Job processed correctly

---

### 3.2 Duplicate Watchdog Events

**Scenario:** File modified multiple times rapidly

**Script:** `test_p3_watchdog_spam.ps1`

```powershell
# Create job file
# Touch/modify 10 times in 100ms
# Verify single processing
```

**Pass Criteria:**
- ✅ 0 duplicate processing
- ✅ Claiming prevents race conditions
- ✅ Debounce works correctly

---

## P4 – 24h Burn-In (The Real Proof) ⏱️

### 4.1 Normal Load Baseline

**Configuration:**
- 10-20 jobs/hour
- Monitor for 24-72 hours

**Metrics to Collect:**
```powershell
# Every hour, log:
- Avg/p95 latency
- Lock timeout warnings count
- failed_reports/ size
- Worker RAM (WorkingSet)
- Worker handle count
- Pending/claimed file count
```

**Monitoring Script:** `monitor_24h_burn_in.ps1`

**Pass Criteria:**
- ✅ RAM/handles stable (no linear growth)
- ✅ No growing `.claimed` files
- ✅ failed_reports ~0 under normal conditions
- ✅ Lock timeout rate <1%
- ✅ No worker crashes

---

### 4.2 Chaos Windows

**Schedule:** 2-3 times during 24h

**Chaos Events:**
1. **Core down 5 min** (hour 8)
2. **Worker restart** (hour 16)
3. **WebRelay restart** (hour 20)

**Pass Criteria:**
- ✅ System recovers automatically
- ✅ No manual intervention needed
- ✅ Jobs continue after recovery

---

## Test Execution Order

### Phase 1: Immediate (Today)
1. ✅ P0.1 - Worker detection fix
2. ✅ P0.2 - State display fix
3. Run quick validation

### Phase 2: Resilience (1-2 hours)
4. P1.1 - Worker kill test
5. P1.2 - Core kill test
6. P1.3 - Power loss test

### Phase 3: Stress (1-2 hours)
7. P2.1 - Multi-worker test
8. P2.2 - Lock stress test
9. P3.1-3.2 - Filesystem tests

### Phase 4: Long-term (24-72 hours)
10. P4.1 - 24h monitoring
11. P4.2 - Chaos windows

---

## Success Thresholds

### 🟢 Green Light (Proceed to Phase 2)
- All P0-P3 tests pass
- 24h burn-in shows stable metrics
- Lock timeout <1% (normal), <5% (stress)
- No corruption, no duplicates

### 🟡 Yellow Light (Investigate)
- 1-2 P1-P3 tests fail with minor issues
- Lock timeout 1-5% (normal load)
- Occasional stale claims (<5)

### 🔴 Red Light (Fix Before Phase 2)
- Any P0 test fails
- State corruption detected
- Duplicate processing occurs
- Worker crashes repeatedly
- Lock timeout >5% (normal load)

---

## Automated Test Runner

**Master Script:** `RUN_ALL_BURN_IN_TESTS.ps1`

```powershell
# Runs P0-P3 in sequence
# Generates report
# Exits with status code
```

**Usage:**
```powershell
.\RUN_ALL_BURN_IN_TESTS.ps1
```

---

## Reporting Template

After each test phase:

```markdown
# Test Results: [Phase Name]

**Date:** [timestamp]
**Duration:** [X] minutes
**Status:** [Green/Yellow/Red]

## Tests Run
- [Test Name]: [PASS/FAIL] - [details]

## Metrics
- [Metric]: [Value]

## Issues Found
1. [Issue] - Severity: [Low/Med/High]

## Recommendation
- [ ] Proceed
- [ ] Fix issues first
- [ ] Rollback
```

---

**Next:** Run P0 fixes, then proceed to P1-P3 automated tests.
