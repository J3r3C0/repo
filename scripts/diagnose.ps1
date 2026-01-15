# Sheratan Diagnostic Bundler (v2.0)
# Collects logs, registry, and state for debugging.

$TOKEN = "shared-secret"
$TS = Get-Date -Format "yyyyMMdd_HHmmss"
$BUNDLE_DIR = Join-Path $PSScriptRoot "diag_$TS"
New-Item -ItemType Directory -Path $BUNDLE_DIR -Force | Out-Null

Write-Host "--- Starting Diagnostic Collection ($TS) ---" -ForegroundColor Cyan

# 1. Collect Hub Health & Metrics
Write-Host "[1/5] Collecting API Metadata..."
try {
    $headers = @{"X-Sheratan-Token" = $TOKEN }
    Invoke-RestMethod -Uri "http://localhost:8787/health" | ConvertTo-Json | Set-Content (Join-Path $BUNDLE_DIR "hub_health_8787.json")
    Invoke-RestMethod -Uri "http://localhost:8788/health" | ConvertTo-Json | Set-Content (Join-Path $BUNDLE_DIR "hub_health_8788.json")
    Invoke-RestMethod -Uri "http://localhost:8787/metrics" -Headers $headers | ConvertTo-Json | Set-Content (Join-Path $BUNDLE_DIR "hub_metrics_control.json")
    Invoke-RestMethod -Uri "http://localhost:8788/metrics" -Headers $headers | ConvertTo-Json | Set-Content (Join-Path $BUNDLE_DIR "hub_metrics_data.json")
    Invoke-RestMethod -Uri "http://localhost:8787/registry" -Headers $headers | ConvertTo-Json | Set-Content (Join-Path $BUNDLE_DIR "registry_snapshot.json")
}
catch {
    Write-Host "Warning: Some API calls failed (Hub may be down)." -ForegroundColor Yellow
}

# 2. Collect Environment Keys (Sanitized)
Write-Host "[2/5] Dumping Environment Keys (Values Scrubbed)..."
Get-ChildItem Env: | Select-Object Name | ConvertTo-Json | Set-Content (Join-Path $BUNDLE_DIR "env_keys.json")

# 3. Collect Logs (Latest 500 lines)
Write-Host "[3/5] Collecting Logs..."
$LOG_FILES = @(
    "C:\gemmaloop\repo_sync_v1\hub_combined.log",
    "C:\gemmaloop\repo_sync_v1\hub_combined_err.log",
    "C:\gemmaloop\.sheratan\logs\hub_security_audit.jsonl",
    "C:\gemmaloop\.sheratan\logs\alerts.jsonl",
    "C:\sauber_main\logs\state_transitions.jsonl"
)

foreach ($f in $LOG_FILES) {
    if (Test-Path $f) {
        $name = Split-Path $f -Leaf
        Get-Content $f -Tail 500 | Set-Content (Join-Path $BUNDLE_DIR "$name.tail")
    }
}

# 4. State Snapshots
if (Test-Path "C:\gemmaloop\.sheratan\state\hub_state.json") {
    Copy-Item "C:\gemmaloop\.sheratan\state\hub_state.json" -Destination $BUNDLE_DIR
}

# 5. Zip it up
Write-Host "[4/5] Creating Bundle..." -ForegroundColor Cyan
$ZIP_PATH = Join-Path $PSScriptRoot "diag_bundle_$TS.zip"
Compress-Archive -Path "$BUNDLE_DIR\*" -DestinationPath $ZIP_PATH -Force

# Cleanup
Remove-Item -Path $BUNDLE_DIR -Recurse -Force

Write-Host "`nBUNDLE CREATED: $ZIP_PATH" -ForegroundColor Green
Write-Host "--- Collection Complete ---" -ForegroundColor Cyan
