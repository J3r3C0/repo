# scripts/acceptance.ps1
# Sheratan Production Acceptance - One Shot PASS/FAIL
# Exit codes:
#   0 = PASS
#   1 = FAIL (generic)
#   2 = FAIL (core not reachable)
#   3 = FAIL (verify scripts failed)
#   4 = FAIL (metrics mismatch)

param(
    [string]$BaseUrl = "http://localhost:8001",
    [switch]$SkipPortCheck,
    [switch]$SkipB2,
    [switch]$SkipB3
)

$ErrorActionPreference = "Stop"

function Write-Section($t) {
    Write-Host ""
    Write-Host "=== $t ==="
}

function Fail($msg, [int]$code = 1) {
    Write-Host ""
    Write-Host "[FAIL] $msg"
    exit $code
}

function Pass($msg) {
    Write-Host "[PASS] $msg"
}

function Try-InvokeJson($url) {
    try {
        return Invoke-RestMethod -Method GET -Uri $url -TimeoutSec 5
    }
    catch {
        return $null
    }
}

function Test-PortInUse($port) {
    $hits = netstat -ano | Select-String -Pattern "[:.]$port\s"
    return ($hits -ne $null)
}

# --- A) Preflight ---
Write-Section "A) Preflight"

$root = (Resolve-Path "$PSScriptRoot\..").Path
Set-Location $root
Pass "Repo root: $root"

if (-not $SkipPortCheck) {
    Write-Section "A1) Port checks"
    if (Test-PortInUse 8001) {
        Pass "Port 8001 appears in use (Core may already be running)."
    }
    else {
        Write-Host "[WARN] Port 8001 not in use. If Core isn't running, the next step will fail."
    }
}

# --- B) Core reachability ---
Write-Section "B) Core Reachability"

$metrics = Try-InvokeJson "$BaseUrl/api/system/metrics"
if ($null -eq $metrics) {
    Fail "Core not reachable at $BaseUrl (try starting core first)" 2
}
Pass "Core reachable: $BaseUrl"

# --- C) Metrics contract ---
Write-Section "C) Metrics Contract"

# Required legacy keys (UI compatibility)
$legacyKeys = @("queueLength", "errorRate", "uptime")
# Required new keys (B1/B2/B3)
$newKeys = @("queue_depth", "inflight", "ready_to_dispatch", "error_rate")

foreach ($k in $legacyKeys) {
    if (-not ($metrics.PSObject.Properties.Name -contains $k)) {
        Fail "Missing legacy metrics key: $k" 4
    }
}
Pass "Legacy metrics keys present"

foreach ($k in $newKeys) {
    if (-not ($metrics.PSObject.Properties.Name -contains $k)) {
        Fail "Missing new metrics key: $k" 4
    }
}
Pass "New metrics keys present (B1)"

# Optional: B2/B3 counters, if you expose them in /api/system/metrics
$optionalKeys = @("idempotent_hits_1m", "idempotent_collisions_1m", "integrity_fail_1m")
foreach ($k in $optionalKeys) {
    if ($metrics.PSObject.Properties.Name -contains $k) {
        Pass "Optional metric present: $k"
    }
    else {
        Write-Host "[WARN] Optional metric not present in /api/system/metrics: $k (ok if tracked elsewhere)"
    }
}

# --- D) Run verify scripts ---
Write-Section "D) Verification Scripts"

if (-not $SkipB2) {
    $b2 = Join-Path $root "scripts\verify_b2_idempotency.ps1"
    if (-not (Test-Path $b2)) { Fail "Missing script: $b2" 3 }
    Write-Host "Running: $b2"
    & $b2
    if ($LASTEXITCODE -ne 0) { Fail "verify_b2_idempotency.ps1 failed (exit $LASTEXITCODE)" 3 }
    Pass "B2 verify passed"
}
else {
    Write-Host "[SKIP] B2 verify"
}

if (-not $SkipB3) {
    $b3 = Join-Path $root "scripts\verify_b3_result_integrity.ps1"
    if (-not (Test-Path $b3)) { Fail "Missing script: $b3" 3 }
    Write-Host "Running: $b3"
    & $b3
    if ($LASTEXITCODE -ne 0) { Fail "verify_b3_result_integrity.ps1 failed (exit $LASTEXITCODE)" 3 }
    Pass "B3 verify passed"
}
else {
    Write-Host "[SKIP] B3 verify"
}

# --- E) Final pass ---
Write-Section "E) Final"

Pass "PRODUCTION ACCEPTANCE: ALL CHECKS GREEN"
exit 0
