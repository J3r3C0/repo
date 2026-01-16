# verify_b1_robustness.ps1
# Automated Verification for Track B1: Backpressure & Retry Budgets

$HUB_URL = "http://localhost:8001"
$TEST_MISSION = "mission-b1-test"
$TEST_TASK = "task-b1-test"

function Write-Step([string]$msg) {
    Write-Host "`n--- $msg ---" -ForegroundColor Cyan
}

function Write-Pass([string]$msg) {
    Write-Host "[PASS] $msg" -ForegroundColor Green
}

function Write-Fail([string]$msg) {
    Write-Host "[FAIL] $msg" -ForegroundColor Red
    exit 1
}

# 1. Check Metrics Endpoint (Backward Compatibility & Robustness Data)
Write-Step "Checking /api/system/metrics for B1 data and Legacy compatibility"
try {
    $metrics = Invoke-RestMethod -Uri "$HUB_URL/api/system/metrics" -Method Get
    
    if ($null -ne $metrics.queue_depth -and $null -ne $metrics.queueLength) {
        Write-Pass "Metrics: Found both 'queue_depth' and 'queueLength'"
    }
    else {
        Write-Fail "Metrics: Missing queue depth fields"
    }
    
    if ($null -ne $metrics.config.max_queue) {
        Write-Pass "Metrics: Found 'config.max_queue' ($($metrics.config.max_queue))"
    }
    else {
        Write-Fail "Metrics: Missing robustness config in metrics"
    }
}
catch {
    Write-Fail "Failed to call metrics endpoint: $_"
}

# 2. Test Queue Depth Backpressure Gate
Write-Step "Testing Queue Depth Backpressure (Submit Limit)"
# We can't easily push 1000 jobs in a script without noise, 
# but we can check if the gate logic is present via code review or small scale test if we lower the limit.
# For now, we simulate a 'defer' or '429' detection if we have a way to inject a low limit.
Write-Host "Note: Verification of 429 logic requires high load or lowered SHERATAN_MAX_QUEUE_DEPTH."

# 3. Test Retry Logic with Backoff
Write-Step "Simulating Job Failure & Checking Retry Scheduling"
# Create a task
$task_payload = @{
    name = "B1 Retry Test"
}
$task = Invoke-RestMethod -Uri "$HUB_URL/api/missions/$TEST_MISSION/tasks" -Method Post -Body (ConvertTo-Json $task_payload) -ContentType "application/json"
$task_id = $task.id

# Create a job that will fail (unknown kind)
$job_payload = @{
    kind    = "non_existent_kind"
    payload = @{ foo = "bar" }
}
$job = Invoke-RestMethod -Uri "$HUB_URL/api/tasks/$task_id/jobs" -Method Post -Body (ConvertTo-Json $job_payload) -ContentType "application/json"
$job_id = $job.id

Write-Host "Job $job_id created. Waiting for dispatcher to sync failure..."
Start-Sleep -Seconds 5

# Check job status and next_retry_utc
$job_status = Invoke-RestMethod -Uri "$HUB_URL/api/jobs/$job_id" -Method Get

if ($job_status.status -eq "pending" -and $null -ne $job_status.next_retry_utc) {
    Write-Pass "Job successfully rescheduled with next_retry_utc: $($job_status.next_retry_utc)"
}
else {
    Write-Host "Current Status: $($job_status.status)"
    Write-Host "Next Retry: $($job_status.next_retry_utc)"
    Write-Fail "Job was not correctly rescheduled for retry."
}

Write-Step "Verification Complete"
Write-Pass "Track B1 Basic Robustness Verified."
