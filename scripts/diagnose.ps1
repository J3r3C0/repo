param (
    [string]$CustomRepoRoot,
    [string]$CustomDataDir
)

$TOKEN = $env:SHERATAN_HUB_TOKEN
if (-not $TOKEN) { 
    $TOKEN = "shared-secret" 
    Write-Host "[WARN] No SHERATAN_HUB_TOKEN found. Using fallback 'shared-secret'." -ForegroundColor Yellow
    Write-Host "[WARN] This is insecure and might not match your production system!" -ForegroundColor Yellow
}

$TS = Get-Date -Format "yyyyMMdd_HHmmss"
$REPO_ROOT = if ($CustomRepoRoot) { $CustomRepoRoot } else { (Resolve-Path "$PSScriptRoot\..").Path }
$DATA_DIR = if ($CustomDataDir) { $CustomDataDir } else { Join-Path $REPO_ROOT "data" }

$BUNDLE_DIR = Join-Path $PSScriptRoot "diag_$TS"
New-Item -ItemType Directory -Path $BUNDLE_DIR -Force | Out-Null

Write-Host "--- Starting Sheratan Core v2 Diagnostic Collection ($TS) ---" -ForegroundColor Cyan
Write-Host "Repo: $REPO_ROOT"

# 1. Collect Hub Health & Metrics
Write-Host "[1/5] Collecting API Metadata (Port 8001)..."
try {
    $headers = @{"X-Sheratan-Token" = $TOKEN }
    Invoke-RestMethod -Uri "http://localhost:8001/api/system/health" | ConvertTo-Json | Set-Content (Join-Path $BUNDLE_DIR "hub_health.json")
    Invoke-RestMethod -Uri "http://localhost:8001/api/system/metrics" -Headers $headers | ConvertTo-Json | Set-Content (Join-Path $BUNDLE_DIR "hub_metrics.json")
    Invoke-RestMethod -Uri "http://localhost:8001/api/system/state" -Headers $headers | ConvertTo-Json | Set-Content (Join-Path $BUNDLE_DIR "state_snapshot.json")
}
catch {
    Write-Host "Warning: API calls failed (System may be down)." -ForegroundColor Yellow
}

# 2. Collect Environment (Sanitized)
Write-Host "[2/5] Collecting Environment (Sanitized)..."
Get-ChildItem Env: | Where-Object { $_.Name -notmatch "TOKEN|SECRET|KEY|PASSWORD|AUTH" } | Select-Object Name, Value | ConvertTo-Json | Set-Content (Join-Path $BUNDLE_DIR "env_sanitized.json")

# 3. Collect Logs (Latest 1000 lines)
Write-Host "[3/5] Collecting Logs..."
$LOG_SOURCES = @(
    (Join-Path $DATA_DIR "logs\hub_security_audit.jsonl"),
    (Join-Path $DATA_DIR "logs\alerts.jsonl"),
    (Join-Path $DATA_DIR "logs\state_transitions.jsonl"),
    (Join-Path $REPO_ROOT "core\core_live_err.log"),
    (Join-Path $REPO_ROOT "core\core_live.log"),
    (Join-Path $REPO_ROOT "core\startup.log"),
    (Join-Path $REPO_ROOT "core\storage_crash.log")
)

foreach ($f in $LOG_SOURCES) {
    if (Test-Path $f) {
        $name = Split-Path $f -Leaf
        Write-Host "  + $name"
        Get-Content $f -Tail 1000 | Set-Content (Join-Path $BUNDLE_DIR "$name.tail")
    }
}

# 4. State & Config Snapshots
Write-Host "[4/5] Collecting Configuration..."
if (Test-Path (Join-Path $REPO_ROOT "runtime\system_state.json")) {
    Copy-Item (Join-Path $REPO_ROOT "runtime\system_state.json") -Destination $BUNDLE_DIR
}
if (Test-Path (Join-Path $REPO_ROOT "config\gateway_config.json")) {
    # Basic sanitize for config if needed, here we just copy
    Copy-Item (Join-Path $REPO_ROOT "config\gateway_config.json") -Destination $BUNDLE_DIR
}

# 5. Zip it up
Write-Host "[5/5] Creating Zip Bundle..." -ForegroundColor Cyan
$ZIP_PATH = Join-Path $PSScriptRoot "diag_bundle_$TS.zip"
if (Get-Command Compress-Archive -ErrorAction SilentlyContinue) {
    Compress-Archive -Path "$BUNDLE_DIR\*" -DestinationPath $ZIP_PATH -Force
    Remove-Item -Path $BUNDLE_DIR -Recurse -Force
    Write-Host "`nBUNDLE CREATED: $ZIP_PATH" -ForegroundColor Green
}
else {
    Write-Host "Warning: Compress-Archive not found. Files left in $BUNDLE_DIR" -ForegroundColor Yellow
}

Write-Host "--- Collection Complete ---" -ForegroundColor Cyan
