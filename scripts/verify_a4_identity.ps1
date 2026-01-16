# verify_a4_identity.ps1
$ErrorActionPreference = "Stop"

$CoreUrl = "http://localhost:8001"
$NodeId = "verify-identity-node"
$PrivKey = "1e23456789abcdef1e23456789abcdef1e23456789abcdef1e23456789abcdef"
$PubKey = "d1303b01b56940f09eb216aaf954c0b66c1a64301fbbb5bd8e4e15c3e3dd2d47"

$AltPriv = "2e23456789abcdef2e23456789abcdef2e23456789abcdef2e23456789abcdef"
$AltPub = "d29139fbd74859fa464eac373fcf99431f5663916812ec813adf532a1da60f14"

function Get-Signature($Payload, $Key = $PrivKey) {
    $json = $Payload | ConvertTo-Json -Compress
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
    $b64 = [Convert]::ToBase64String($bytes)
    $sig = python scripts\sign_helper.py "$b64" $Key
    return $sig.Trim()
}

function Send-Heartbeat($Payload) {
    Write-Host "Sending Heartbeat from $NodeId" -ForegroundColor Gray
    $Response = Invoke-RestMethod -Uri "$CoreUrl/api/hosts/heartbeat" -Method Post -Body ($Payload | ConvertTo-Json) -ContentType "application/json"
    return $Response
}

Write-Host "=== Track A4: Node Identity Verification ===" -ForegroundColor Yellow

# T1: TOFU Pinning
Write-Host "`n[T1] Testing TOFU (Trust On First Use)" -ForegroundColor Cyan
$p1 = @{ host_id = $NodeId; public_key = $PubKey; attestation = @{ build_id = "v4"; capability_hash = "h4" } }
$p1.signature = Get-Signature $p1

Send-Heartbeat $p1
Write-Host "[PASS] T1: Initial heartbeat sent with identity." -ForegroundColor Green

# T2: Valid Signature
Write-Host "`n[T2] Testing Valid Signature (Repeat)" -ForegroundColor Cyan
$p2 = @{ host_id = $NodeId; public_key = $PubKey; attestation = @{ build_id = "v4"; capability_hash = "h4" } }
$p2.signature = Get-Signature $p2
Send-Heartbeat $p2
Write-Host "[PASS] T2: Repeat heartbeat with valid signature." -ForegroundColor Green

# T3: Key Mismatch (Attempt spoof with another key)
Write-Host "`n[T3] Testing Key Mismatch (Spoof attempt)" -ForegroundColor Cyan
$p3 = @{ host_id = $NodeId; public_key = $AltPub; attestation = @{ build_id = "v4"; capability_hash = "h4" } }
# Sign with alt key
$p3.signature = Get-Signature $p3 $AltPriv

Send-Heartbeat $p3
Write-Host "[INFO] T3: Sent heartbeat with wrong key. Checking alerts.jsonl..." -ForegroundColor Gray
Start-Sleep -Seconds 1

$alerts = Get-Content data/logs/alerts.jsonl | Select-Object -Last 5
if ($alerts -match "IDENTITY_KEY_MISMATCH") {
    Write-Host "[PASS] T3: Key mismatch detected and logged." -ForegroundColor Green
}
else {
    Write-Host "[FAIL] T3: Identity error not found in alerts.jsonl" -ForegroundColor Red
    Write-Host "Last 10 alerts:" -ForegroundColor Gray
    Get-Content data/logs/alerts.jsonl | Select-Object -Last 10
}

# T4: Invalid Signature (Corrupted payload)
Write-Host "`n[T4] Testing Invalid Signature" -ForegroundColor Cyan
$p4 = @{ host_id = $NodeId; public_key = $PubKey; attestation = @{ build_id = "v4"; capability_hash = "h4" } }
$sig4 = Get-Signature $p4
$p4.signature = $sig4
$p4.attestation.build_id = "HACKED" # Corrupt after signing

Send-Heartbeat $p4
Start-Sleep -Seconds 1
$alerts = Get-Content data/logs/alerts.jsonl | Select-Object -Last 5
if ($alerts -match "IDENTITY_INVALID_SIGNATURE") {
    Write-Host "[PASS] T4: Invalid signature detected." -ForegroundColor Green
}
else {
    Write-Host "[FAIL] T4: Invalid signature not signaled." -ForegroundColor Red
}

Write-Host "`n=== Verification Track A4 Complete ===" -ForegroundColor Yellow
