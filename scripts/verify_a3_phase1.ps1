# verify_a3_phase1.ps1
$ErrorActionPreference = "Stop"

$CoreUrl = "http://localhost:8001"
$Endpoint = "$CoreUrl/api/hosts/heartbeat"
$NodeId = "verify-node-A3"
$AlertsFile = "c:\sauber_main\data\logs\alerts.jsonl"

function Send-Heartbeat($Payload) {
    Write-Host "Sending Heartbeat: $($Payload.attestation.build_id) / $($Payload.attestation.capability_hash)" -ForegroundColor Gray
    $Response = Invoke-RestMethod -Uri $Endpoint -Method Post -Body ($Payload | ConvertTo-Json) -ContentType "application/json"
    return $Response
}

function Get-LastAlert() {
    if (Test-Path $AlertsFile) {
        $lines = @(Get-Content $AlertsFile | Where-Object { $_.Trim() -ne "" })
        if ($lines.Count -gt 0) {
            return $lines[-1] | ConvertFrom-Json
        }
    }
    return $null
}

Write-Host "=== Track A3 Phase 1: Policy Verification (Stateless) ===" -ForegroundColor Yellow

# T0: Initial Clear
if (Test-Path $AlertsFile) { Remove-Item $AlertsFile }

# T1: DRIFT => POLICY_WARN
Write-Host "`n[T1] Testing DRIFT -> POLICY_WARN" -ForegroundColor Cyan
# First seen to establish baseline
$null = Send-Heartbeat @{
    host_id     = $NodeId
    attestation = @{ build_id = "v1"; capability_hash = "hash-A"; runtime = @{ os = "win" } }
}
# Now DRIFT
$res = Send-Heartbeat @{
    host_id     = $NodeId
    attestation = @{ build_id = "v1-drifted"; capability_hash = "hash-A"; runtime = @{ os = "win" } }
}

$lastAlert = Get-LastAlert
if ($lastAlert -and $lastAlert.event -eq "POLICY_WARN" -and $lastAlert.details.host_id -eq $NodeId) {
    Write-Host "[PASS] T1: POLICY_WARN alert recorded correctly." -ForegroundColor Green
}
else {
    Write-Host "[FAIL] T1: Expected POLICY_WARN alert. Got: $($lastAlert | ConvertTo-Json -Compress)" -ForegroundColor Red
}

# T2: SPOOF_SUSPECT => POLICY_QUARANTINE (Flip-Flop)
Write-Host "`n[T2] Testing SPOOF_SUSPECT -> POLICY_QUARANTINE" -ForegroundColor Cyan
# Send rapid changes (3 changes needed)
$null = Send-Heartbeat @{ host_id = $NodeId; attestation = @{ build_id = "v1"; capability_hash = "hash-B" } }
$null = Send-Heartbeat @{ host_id = $NodeId; attestation = @{ build_id = "v1"; capability_hash = "hash-C" } }
$res = Send-Heartbeat @{ host_id = $NodeId; attestation = @{ build_id = "v1"; capability_hash = "hash-D" } }

$lastAlert = Get-LastAlert
if ($lastAlert -and $lastAlert.event -eq "POLICY_QUARANTINED" -and $lastAlert.details.host_id -eq $NodeId) {
    Write-Host "[PASS] T2: POLICY_QUARANTINED alert recorded correctly." -ForegroundColor Green
}
else {
    Write-Host "[FAIL] T2: Expected POLICY_QUARANTINED alert. Got: $($lastAlert | ConvertTo-Json -Compress)" -ForegroundColor Red
}

# T3: No-Spam / Repeatability Check
Write-Host "`n[T3] Testing No-Spam (Repeat DRIFT)" -ForegroundColor Cyan
$null = Send-Heartbeat @{ host_id = $NodeId; attestation = @{ build_id = "v1-drifted"; capability_hash = "hash-A" } }
$null = Send-Heartbeat @{ host_id = $NodeId; attestation = @{ build_id = "v1-drifted"; capability_hash = "hash-A" } }

$alertsCount = (Get-Content $AlertsFile).Count
Write-Host "Total alerts in file: $alertsCount" -ForegroundColor Gray
Write-Host "[INFO] A3 Phase 1 (Stateless) currently records 1 alert per heartbeat while policy is active." -ForegroundColor Yellow

Write-Host "`n=== Verification Phase 1 Complete ===" -ForegroundColor Yellow
