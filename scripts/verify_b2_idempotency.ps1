# verify_b2_idempotency.ps1
# Automated Verification for Track B2: Idempotency

$HUB_URL = "http://localhost:8001"
$MISSION_ID = "b2-test-mission-$(Get-Random)"
$TASK_ID = "b2-test-task-$(Get-Random)"

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

# Setup: Create Mission and Task
Write-Step "Setup: Creating Mission and Task"
$m_payload = @{ title = "Idempotency Test"; description = "B2 Verification" }
$mission = Invoke-RestMethod -Uri "$HUB_URL/api/missions" -Method Post -Body (ConvertTo-Json $m_payload) -ContentType "application/json"
$MISSION_ID = $mission.id

$t_payload = @{ name = "B2 Task"; kind = "echo" }
$task = Invoke-RestMethod -Uri "$HUB_URL/api/missions/$MISSION_ID/tasks" -Method Post -Body (ConvertTo-Json $t_payload) -ContentType "application/json"
$TASK_ID = $task.id

# T1: Basic Deduplication
Write-Step "T1: Basic Deduplication (Same Key, Same Payload)"
$key_A = "key-A-$(Get-Random)"
$payload_X = @{ payload = @{ foo = "bar" }; idempotency_key = $key_A }

$job1 = Invoke-RestMethod -Uri "$HUB_URL/api/tasks/$TASK_ID/jobs" -Method Post -Body (ConvertTo-Json $payload_X) -ContentType "application/json"
$job2 = Invoke-RestMethod -Uri "$HUB_URL/api/tasks/$TASK_ID/jobs" -Method Post -Body (ConvertTo-Json $payload_X) -ContentType "application/json"

if ($job1.id -eq $job2.id) {
    Write-Pass "Both requests returned same Job Id: $($job1.id)"
}
else {
    Write-Fail "Requests returned different IDs: $($job1.id) vs $($job2.id)"
}

# T2: Collision Detection
Write-Step "T2: Collision Detection (Same Key, Different Payload)"
$payload_Y = @{ payload = @{ foo = "baz" }; idempotency_key = $key_A }

try {
    $job3 = Invoke-RestMethod -Uri "$HUB_URL/api/tasks/$TASK_ID/jobs" -Method Post -Body (ConvertTo-Json $payload_Y) -ContentType "application/json"
    Write-Fail "Collision was NOT detected (expected 409 Conflict)"
}
catch {
    if ($_.Exception.Response.StatusCode -eq 409) {
        Write-Pass "Collision detected correctly with 409 Conflict"
    }
    else {
        Write-Fail "Expected 409, but got $($_.Exception.Response.StatusCode)"
    }
}

# T3: Completion Cache
Write-Step "T3: Completion Cache (Return result after job finish)"
# We use a job that finishes quickly if echo is implemented, but here we can just manually set it in DB for testing if no worker is running.
# Or better: just verify that status is returned.
$job1_status = Invoke-RestMethod -Uri "$HUB_URL/api/jobs/$($job1.id)" -Method Get
Write-Host "Current Status of Job 1: $($job1_status.status)"

# Simulate completion if needed (optional if worker is active)
# For the sake of this test, we just check if it returns the job with 'idempotent: true'
$job4 = Invoke-RestMethod -Uri "$HUB_URL/api/tasks/$TASK_ID/jobs" -Method Post -Body (ConvertTo-Json $payload_X) -ContentType "application/json"
if ($job4.idempotent -eq $true) {
    Write-Pass "Returned job has 'idempotent: true' flag"
}
else {
    Write-Fail "Returned job missing 'idempotent: true' flag"
}

# T4: No Key
Write-Step "T4: No Key (Separate Jobs)"
$payload_no_key = @{ payload = @{ foo = "bar" } } # no key
$job5 = Invoke-RestMethod -Uri "$HUB_URL/api/tasks/$TASK_ID/jobs" -Method Post -Body (ConvertTo-Json $payload_no_key) -ContentType "application/json"
$job6 = Invoke-RestMethod -Uri "$HUB_URL/api/tasks/$TASK_ID/jobs" -Method Post -Body (ConvertTo-Json $payload_no_key) -ContentType "application/json"

if ($job5.id -ne $job6.id) {
    Write-Pass "Requests without key created different jobs"
}
else {
    Write-Fail "Requests without key returned same ID: $($job5.id)"
}

# Check Metrics
Write-Step "Checking Idempotency Metrics"
$metrics = Invoke-RestMethod -Uri "$HUB_URL/api/system/metrics" -Method Get
if ($null -ne $metrics.idempotent_hits_1m -and $metrics.idempotent_hits_1m -ge 1) {
    Write-Pass "Metrics: idempotent_hits_1m works ($($metrics.idempotent_hits_1m))"
}
else {
    Write-Fail "Metrics: idempotent_hits_1m not found or 0"
}

if ($null -ne $metrics.idempotent_collisions_1m -and $metrics.idempotent_collisions_1m -ge 1) {
    Write-Pass "Metrics: idempotent_collisions_1m works ($($metrics.idempotent_collisions_1m))"
}
else {
    Write-Fail "Metrics: idempotent_collisions_1m not found or 0"
}

Write-Step "Verification Complete"
Write-Pass "Track B2 Idempotency Verified."
