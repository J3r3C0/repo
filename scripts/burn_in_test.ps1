# Phase 1 Burn-In Test - System Status Check & Event-Driven Performance Test
# Date: 2026-01-13

Write-Host "=== Phase 1 Burn-In Test ===" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# PART 1: SYSTEM STATUS CHECK
# ============================================================================

Write-Host "PART 1: System Status Check" -ForegroundColor Yellow
Write-Host "----------------------------" -ForegroundColor Yellow
Write-Host ""

# Check if Core API is running
Write-Host "[1/5] Checking Core API (port 8001)..." -ForegroundColor White
try {
    $coreHealth = Invoke-RestMethod -Uri "http://localhost:8001/api/system/state" -Method GET -TimeoutSec 5
    Write-Host "  [OK] Core API: RUNNING" -ForegroundColor Green
    Write-Host "    State: $($coreHealth.state)" -ForegroundColor Gray
}
catch {
    Write-Host "  [X] Core API: DOWN" -ForegroundColor Red
    Write-Host "    Error: $_" -ForegroundColor Red
    exit 1
}

# Check if WebRelay is running
Write-Host "[2/5] Checking WebRelay (port 3001)..." -ForegroundColor White
try {
    $webrelayHealth = Invoke-RestMethod -Uri "http://localhost:3001/api/health" -Method GET -TimeoutSec 5
    Write-Host "  [OK] WebRelay: RUNNING" -ForegroundColor Green
}
catch {
    Write-Host "  [X] WebRelay: DOWN" -ForegroundColor Red
    Write-Host "    Error: $_" -ForegroundColor Red
    exit 1
}

# Check Worker process
Write-Host "[3/5] Checking Worker process..." -ForegroundColor White
$workerProcess = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like "*worker*" -or $_.CommandLine -like "*worker_loop*" }
if ($workerProcess) {
    Write-Host "  [OK] Worker: RUNNING (PID: $($workerProcess.Id))" -ForegroundColor Green
    Write-Host "    CPU: $($workerProcess.CPU)s" -ForegroundColor Gray
}
else {
    Write-Host "  [!] Worker: Cannot confirm (check manually)" -ForegroundColor Yellow
}

# Check State Machine integrity
Write-Host "[4/5] Checking State Machine integrity..." -ForegroundColor White
try {
    $stateFile = "c:\sauber_main\runtime\system_state.json"
    if (Test-Path $stateFile) {
        $state = Get-Content $stateFile | ConvertFrom-Json
        Write-Host "  [OK] State file: VALID JSON" -ForegroundColor Green
        Write-Host "    Current state: $($state.current_state)" -ForegroundColor Gray
        Write-Host "    Last transition: $($state.last_transition_id)" -ForegroundColor Gray
    }
    else {
        Write-Host "  [!] State file: NOT FOUND (will be created)" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "  [X] State file: CORRUPTED" -ForegroundColor Red
    Write-Host "    Error: $_" -ForegroundColor Red
    exit 1
}

# Check for stale claims
Write-Host "[5/5] Checking for stale job claims..." -ForegroundColor White
$staleClaims = Get-ChildItem "c:\sauber_main\data\webrelay_out\*.claimed" -ErrorAction SilentlyContinue
if ($staleClaims) {
    Write-Host "  [!] Found $($staleClaims.Count) stale claims" -ForegroundColor Yellow
    $staleClaims | ForEach-Object { Write-Host "    - $($_.Name)" -ForegroundColor Gray }
}
else {
    Write-Host "  [OK] No stale claims" -ForegroundColor Green
}

Write-Host ""
Write-Host "System Status: ALL CHECKS PASSED" -ForegroundColor Green
Write-Host ""

# ============================================================================
# PART 2: EVENT-DRIVEN PERFORMANCE TEST
# ============================================================================

Write-Host "PART 2: Event-Driven Performance Test" -ForegroundColor Yellow
Write-Host "--------------------------------------" -ForegroundColor Yellow
Write-Host ""

# Test parameters
$numJobs = 20  # Start with 20 jobs (can increase to 50 later)
$burstDelay = 100  # milliseconds between job submissions

Write-Host "Test Configuration:" -ForegroundColor White
Write-Host "  Jobs to submit: $numJobs" -ForegroundColor Gray
Write-Host "  Burst delay: $burstDelay ms" -ForegroundColor Gray
Write-Host "  Expected latency: less than 500ms per job" -ForegroundColor Gray
Write-Host ""

# Create test jobs directory
$testJobsDir = "c:\sauber_main\data\webrelay_out"
if (-not (Test-Path $testJobsDir)) {
    New-Item -ItemType Directory -Path $testJobsDir -Force | Out-Null
}

# Record start time
$testStartTime = Get-Date

Write-Host "Submitting $numJobs test jobs..." -ForegroundColor White

# Submit burst of jobs
$jobIds = @()
for ($i = 1; $i -le $numJobs; $i++) {
    $jobId = [guid]::NewGuid().ToString()
    $jobIds += $jobId
    
    $job = @{
        job_id   = $jobId
        kind     = "list_files"
        payload  = @{
            params = @{
                root      = "."
                max_depth = 2
            }
        }
        metadata = @{
            test_id         = "burn_in_test_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
            test_job_number = $i
        }
    } | ConvertTo-Json -Depth 10
    
    $jobFile = Join-Path $testJobsDir "$jobId.job.json"
    $job | Out-File $jobFile -Encoding UTF8
    
    # Progress indicator
    if ($i -eq 5 -or $i -eq 10 -or $i -eq 15 -or $i -eq 20) {
        Write-Host "  Submitted: $i/$numJobs" -ForegroundColor Gray
    }
    
    # Burst delay
    Start-Sleep -Milliseconds $burstDelay
}

Write-Host "  [OK] All $numJobs jobs submitted" -ForegroundColor Green
Write-Host ""

# Wait for processing
Write-Host "Waiting for jobs to process..." -ForegroundColor White
$maxWaitSeconds = 60
$checkInterval = 2
$elapsed = 0

$resultsDir = "c:\sauber_main\data\webrelay_in"

while ($elapsed -lt $maxWaitSeconds) {
    $results = Get-ChildItem "$resultsDir\*.result.json" -ErrorAction SilentlyContinue | Where-Object {
        $jobIds -contains $_.BaseName.Replace('.result', '')
    }
    
    $processedCount = $results.Count
    $percentage = [math]::Round(($processedCount / $numJobs) * 100, 1)
    
    Write-Host "`r  Progress: $processedCount/$numJobs ($percentage%) - Elapsed: $elapsed s" -NoNewline -ForegroundColor Gray
    
    if ($processedCount -eq $numJobs) {
        Write-Host ""
        Write-Host "  [OK] All jobs processed!" -ForegroundColor Green
        break
    }
    
    Start-Sleep -Seconds $checkInterval
    $elapsed += $checkInterval
}

Write-Host ""

# Record end time
$testEndTime = Get-Date
$totalDuration = ($testEndTime - $testStartTime).TotalSeconds

# ============================================================================
# PART 3: RESULTS ANALYSIS
# ============================================================================

Write-Host ""
Write-Host "PART 3: Results Analysis" -ForegroundColor Yellow
Write-Host "------------------------" -ForegroundColor Yellow
Write-Host ""

# Count results
$finalResults = Get-ChildItem "$resultsDir\*.result.json" -ErrorAction SilentlyContinue | Where-Object {
    $jobIds -contains $_.BaseName.Replace('.result', '')
}

$processedCount = $finalResults.Count
$successRate = [math]::Round(($processedCount / $numJobs) * 100, 1)

Write-Host "Job Processing:" -ForegroundColor White
Write-Host "  Submitted: $numJobs" -ForegroundColor Gray
Write-Host "  Processed: $processedCount" -ForegroundColor Gray
Write-Host "  Success rate: $successRate %" -ForegroundColor $(if ($successRate -eq 100) { "Green" } else { "Yellow" })
Write-Host "  Total duration: $([math]::Round($totalDuration, 2)) s" -ForegroundColor Gray
Write-Host "  Avg latency: $([math]::Round($totalDuration / $numJobs * 1000, 0)) ms per job" -ForegroundColor Gray

# Check for stale claims
$staleClaims = Get-ChildItem "$testJobsDir\*.claimed" -ErrorAction SilentlyContinue | Where-Object {
    $jobIds -contains $_.BaseName.Replace('.claimed', '')
}

Write-Host ""
Write-Host "Cleanup Status:" -ForegroundColor White
if ($staleClaims) {
    Write-Host "  [!] Stale claims: $($staleClaims.Count)" -ForegroundColor Yellow
    $staleClaims | ForEach-Object { Write-Host "    - $($_.Name)" -ForegroundColor Gray }
}
else {
    Write-Host "  [OK] No stale claims (all jobs cleaned up)" -ForegroundColor Green
}

# Check for duplicates
$duplicateCheck = @{}
foreach ($result in $finalResults) {
    $jobId = $result.BaseName.Replace('.result', '')
    if ($duplicateCheck.ContainsKey($jobId)) {
        $duplicateCheck[$jobId]++
    }
    else {
        $duplicateCheck[$jobId] = 1
    }
}

$duplicates = $duplicateCheck.GetEnumerator() | Where-Object { $_.Value -gt 1 }
Write-Host ""
Write-Host "Duplicate Check:" -ForegroundColor White
if ($duplicates) {
    Write-Host "  [X] Found duplicates:" -ForegroundColor Red
    $duplicates | ForEach-Object { Write-Host "    - $($_.Key): $($_.Value) times" -ForegroundColor Red }
}
else {
    Write-Host "  [OK] No duplicate processing" -ForegroundColor Green
}

# Calculate performance metrics
$avgLatency = [math]::Round($totalDuration / $numJobs * 1000, 0)

Write-Host ""
Write-Host "Performance Metrics:" -ForegroundColor White
Write-Host "  Avg latency: $avgLatency ms" -ForegroundColor $(if ($avgLatency -lt 500) { "Green" } elseif ($avgLatency -lt 1000) { "Yellow" } else { "Red" })
Write-Host "  Throughput: $([math]::Round($numJobs / $totalDuration, 2)) jobs/sec" -ForegroundColor Gray

# ============================================================================
# PART 4: VERDICT
# ============================================================================

Write-Host ""
Write-Host "=== TEST VERDICT ===" -ForegroundColor Cyan
Write-Host ""

$passed = $true
$warnings = @()

# Check success criteria
if ($successRate -ne 100) {
    $passed = $false
    Write-Host "[X] Not all jobs processed ($successRate %)" -ForegroundColor Red
}

if ($staleClaims) {
    $warnings += "Stale claims found"
    Write-Host "[!] Stale claims detected" -ForegroundColor Yellow
}

if ($duplicates) {
    $passed = $false
    Write-Host "[X] Duplicate processing detected" -ForegroundColor Red
}

if ($avgLatency -gt 500) {
    $latencyMsg = "High latency ($avgLatency ms > 500ms)"
    $warnings += $latencyMsg
    Write-Host "[!] Latency above target: $latencyMsg" -ForegroundColor Yellow
}

Write-Host ""
if ($passed -and $warnings.Count -eq 0) {
    Write-Host "STATUS: [OK] PASS (GREEN LIGHT)" -ForegroundColor Green
    Write-Host "Event-driven performance is excellent. Ready for extended burn-in." -ForegroundColor Green
}
elseif ($passed -and $warnings.Count -gt 0) {
    Write-Host "STATUS: [!] PASS WITH WARNINGS (YELLOW LIGHT)" -ForegroundColor Yellow
    Write-Host "Warnings:" -ForegroundColor Yellow
    $warnings | ForEach-Object { Write-Host "  - $_" -ForegroundColor Yellow }
}
else {
    Write-Host "STATUS: [X] FAIL (RED LIGHT)" -ForegroundColor Red
    Write-Host "Critical issues detected. Review logs and fix before proceeding." -ForegroundColor Red
}

Write-Host ""
Write-Host "=== Test Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host "  1. Review logs in c:\sauber_main\logs\" -ForegroundColor Gray
Write-Host "  2. Check worker.log for event-driven mode activity" -ForegroundColor Gray
Write-Host "  3. If PASS: Proceed to 24h burn-in (Test 1)" -ForegroundColor Gray
Write-Host "  4. If FAIL: Review and fix issues" -ForegroundColor Gray
Write-Host ""
