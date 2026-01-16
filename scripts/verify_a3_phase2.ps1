# verify_a3_phase2.ps1
$ErrorActionPreference = "Stop"

$CoreUrl = "http://localhost:8001"
$NodeId = "verify-node-A3-persistent"
$AlertsFile = "c:\sauber_main\data\logs\alerts.jsonl"

function Send-Heartbeat($Payload) {
    Write-Host "Sending Heartbeat from $NodeId" -ForegroundColor Gray
    $Response = Invoke-RestMethod -Uri "$CoreUrl/api/hosts/heartbeat" -Method Post -Body ($Payload | ConvertTo-Json) -ContentType "application/json"
    return $Response
}

function Get-Policies() {
    return Invoke-RestMethod -Uri "$CoreUrl/api/admin/policies" -Method Get
}

function Clear-Policy($TargetId) {
    $Payload = @{ host_id = $TargetId }
    return Invoke-RestMethod -Uri "$CoreUrl/api/admin/policies/clear" -Method Post -Body ($Payload | ConvertTo-Json) -ContentType "application/json"
}

Write-Host "=== Track A3 Phase 2: Response & Persistence Verification ===" -ForegroundColor Yellow

# T1: Trigger Persistent Quarantine
Write-Host "`n[T1] Triggering Quarantine (SPOOF_SUSPECT Flip-Flop)" -ForegroundColor Cyan
# Send 5 changes to surely cross the threshold of 3
for ($i = 1; $i -le 5; $i++) {
    Send-Heartbeat @{ host_id = $NodeId; attestation = @{ build_id = "v2-$i"; capability_hash = "hash-$i" } }
    Start-Sleep -Seconds 1
}

# T2: Check Persistence in Admin API
Write-Host "`n[T2] Checking Admin Policy List" -ForegroundColor Cyan
$policies = Get-Policies
$myPolicy = $policies | Where-Object { $_.id -eq $NodeId }

if ($myPolicy -and $myPolicy.policy_state -eq "QUARANTINED") {
    Write-Host "[PASS] T2: Policy persisted in DB. Reason: $($myPolicy.policy_reason), Expires: $($myPolicy.policy_until_utc)" -ForegroundColor Green
}
else {
    Write-Host "[FAIL] T2: Policy not found or wrong state. Got: $($policies | ConvertTo-Json -Compress)" -ForegroundColor Red
}

# T3: Manual Clear
Write-Host "`n[T3] Testing Admin Manual Clear" -ForegroundColor Cyan
$res = Clear-Policy -TargetId $NodeId
Write-Host "Clear result: $($res.message)" -ForegroundColor Gray

$policiesAfter = Get-Policies
$myPolicyAfter = $policiesAfter | Where-Object { $_.id -eq $NodeId }

if (-not $myPolicyAfter) {
    Write-Host "[PASS] T3: Policy cleared successfully." -ForegroundColor Green
}
else {
    Write-Host "[FAIL] T3: Policy still active after clear." -ForegroundColor Red
}

Write-Host "`n=== Verification Phase 2 Complete ===" -ForegroundColor Yellow
