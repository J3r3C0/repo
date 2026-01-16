# verify_b3_result_integrity.ps1
# Verification script for Track B3: Result Integrity

$HUB_URL = "http://localhost:8001"
$DB_PATH = "data/sheratan.db"

function Write-Header($msg) {
    Write-Host "`n--- $msg ---" -ForegroundColor Cyan
}

function Assert-Status($response, $expected, $msg) {
    if ($response.StatusCode -eq $expected) {
        Write-Host "[PASS] $msg (Got $expected)" -ForegroundColor Green
    }
    else {
        Write-Host "[FAIL] $msg (Expected $expected, got $($response.StatusCode))" -ForegroundColor Red
        exit 1
    }
}

# --- Setup: Creating Mission and Task ---
Write-Header "Setup: Creating Context"
$mission = Invoke-RestMethod -Uri "$HUB_URL/api/missions" -Method Post -Body (@{title = "Integrity Test"; description = "Testing B3" } | ConvertTo-Json) -ContentType "application/json"
$MISSION_ID = $mission.id
$task = Invoke-RestMethod -Uri "$HUB_URL/api/missions/$MISSION_ID/tasks" -Method Post -Body (@{name = "Integrity Task"; kind = "test" } | ConvertTo-Json) -ContentType "application/json"
$TASK_ID = $task.id

# --- T1: Valid Result Integrity ---
Write-Header "T1: Valid Result Integrity"
$key1 = "integrity_test_key_" + (Get-Date -UFormat "%s")
$payload1 = @{ action = "test"; target = "integrity" }
$job1 = Invoke-RestMethod -Uri "$HUB_URL/api/tasks/$TASK_ID/jobs" -Method Post -Body (@{idempotency_key = $key1; payload = $payload1 } | ConvertTo-Json) -ContentType "application/json"
$JOB_ID = $job1.id

# Mock completion via sync
$sync_body = @{
    status = "completed"
    result = @{ success = $true; output = "Integrity is good" }
} | ConvertTo-Json
Invoke-RestMethod -Uri "$HUB_URL/api/jobs/$JOB_ID/sync" -Method Post -Body $sync_body -ContentType "application/json" | Out-Null

# Request again (Idempotent return)
try {
    $job1_check = Invoke-RestMethod -Uri "$HUB_URL/api/tasks/$TASK_ID/jobs" -Method Post -Body (@{idempotency_key = $key1; payload = $payload1 } | ConvertTo-Json) -ContentType "application/json"
    Write-Host "[PASS] Valid Result retrieved successfully: $($job1_check.id)" -ForegroundColor Green
}
catch {
    Write-Host "[FAIL] Valid Result retrieval failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# --- T2: Tamper Detection ---
Write-Header "T2: Tamper Detection"
Write-Host "Manually tampering with DB..."
# We use sqlite3 to update the DB directly. Use escaped quotes for SQLite.
sqlite3 $DB_PATH "UPDATE jobs SET completed_result = '{\""tampered\"":true}' WHERE id = '$JOB_ID';"
$check = sqlite3 $DB_PATH "SELECT completed_result FROM jobs WHERE id = '$JOB_ID'"
Write-Host "Current DB Value: $check"

try {
    Write-Host "Sending request for tampered job..."
    $resp = Invoke-WebRequest -Uri "$HUB_URL/api/tasks/$TASK_ID/jobs" -Method Post -Body (@{idempotency_key = $key1; payload = $payload1 } | ConvertTo-Json) -ContentType "application/json" -ErrorAction Stop -TimeoutSec 10
    Write-Host "[FAIL] Expected 403 for tampered data, but got $($resp.StatusCode)" -ForegroundColor Red
    exit 1
}
catch {
    Write-Host "Caught exception: $($_.Exception.Message)"
    if ($_.Exception.Response -and $_.Exception.Response.StatusCode -eq "Forbidden") {
        Write-Host "[PASS] Tampered data rejected with 403 Forbidden" -ForegroundColor Green
    }
    elseif ($_.Exception.Response) {
        Write-Host "[FAIL] Expected 403, but got $($_.Exception.Response.StatusCode)" -ForegroundColor Red
        # Print actual error for debugging
        $errorBody = $_.Exception.Response.GetResponseStream()
        $reader = New-Object System.IO.StreamReader($errorBody)
        Write-Host "Error details: $($reader.ReadToEnd())"
        exit 1
    }
    else {
        Write-Host "[FAIL] Request failed without a response: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
}

# --- T3: Soft Migration (Compute-on-read) ---
Write-Header "T3: Soft Migration"
$key3 = "migrate_test_key_" + (Get-Date -UFormat "%s")
$job3 = Invoke-RestMethod -Uri "$HUB_URL/api/tasks/$TASK_ID/jobs" -Method Post -Body (@{idempotency_key = $key3; payload = $payload1 } | ConvertTo-Json) -ContentType "application/json"
$JOB3_ID = $job3.id

# Simulate completed job without hash (manual DB insert/update)
sqlite3 $DB_PATH "UPDATE jobs SET status = 'completed', completed_result = '{\""migrated\"":true}', result_hash = NULL WHERE id = '$JOB3_ID'"

Write-Host "Requesting job with missing hash (triggering soft migrate)..."
try {
    $job3_ret = Invoke-RestMethod -Uri "$HUB_URL/api/tasks/$TASK_ID/jobs" -Method Post -Body (@{idempotency_key = $key3; payload = $payload1 } | ConvertTo-Json) -ContentType "application/json"
    Write-Host "[PASS] Job with missing hash successfully migrated and returned" -ForegroundColor Green
    
    # Verify hash exists in DB now
    $db_hash = sqlite3 $DB_PATH "SELECT result_hash FROM jobs WHERE id = '$JOB3_ID'"
    if ($db_hash) {
        Write-Host "[PASS] Hash persisted to DB: $db_hash" -ForegroundColor Green
    }
    else {
        Write-Host "[FAIL] Hash not persisted during migration" -ForegroundColor Red
        exit 1
    }
}
catch {
    Write-Host "[FAIL] Migration request failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# --- Checking Metrics ---
Write-Header "Checking Metrics"
$metrics = Invoke-RestMethod -Uri "$HUB_URL/api/system/metrics"
if ($metrics.integrity_fail_1m -ge 1) {
    Write-Host "[PASS] integrity_fail_1m metric verified: $($metrics.integrity_fail_1m)" -ForegroundColor Green
}
else {
    Write-Host "[FAIL] integrity_fail_1m metric not incremented" -ForegroundColor Red
}

Write-Header "Verification Complete"
Write-Host "[PASS] Track B3 Result Integrity Verified." -ForegroundColor Green
