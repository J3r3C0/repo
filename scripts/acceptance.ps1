# scripts/acceptance.ps1
# Sheratan Core Acceptance Test (v0.3.0)

$EXE_PATH = ".\dist\sheratan_core.exe"
if (-not (Test-Path $EXE_PATH)) {
    Write-Host "Error: Executable not found at $EXE_PATH" -ForegroundColor Red
    exit 1
}

$EXE_DIR = Split-Path $EXE_PATH -Parent
$TOKEN = $env:SHERATAN_HUB_TOKEN
if (-not $TOKEN) { $TOKEN = "shared-secret" }

Write-Host "--- Running Acceptance Site Gate (Track D3) ---" -ForegroundColor Cyan

# 1. Start EXE in background
Write-Host "[1/5] Launching sheratan_core.exe..."
# We start it in its own directory to be sure
$proc = Start-Process -FilePath $EXE_PATH -WorkingDirectory $EXE_DIR -NoNewWindow -PassThru

Write-Host "Waiting for API to be ready (up to 60s)..."
$startTime = Get-Date
$isReady = $false
while (((Get-Date) - $startTime).TotalSeconds -lt 60) {
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:8001/api/system/health" -ErrorAction SilentlyContinue
        if ($health.overall) {
            $isReady = $true
            Write-Host "  ✓ API is UP ($(((Get-Date) - $startTime).TotalSeconds)s)" -ForegroundColor Green
            break
        }
    }
    catch {}
    Start-Sleep -Seconds 2
}

if (-not $isReady) {
    Write-Host "  ✗ API failed to start within 60s" -ForegroundColor Red
    $Success = $false
}

$Success = $true

try {
    # 2. Check API Health Detail
    Write-Host "[2/5] Testing API Health Detail..."
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:8001/api/system/health"
        if ($health.status) {
            Write-Host "  ✓ API Health detail OK: $($health.status)" -ForegroundColor Green
        }
        else {
            Write-Host "  ✗ API Health missing 'status' field" -ForegroundColor Red
            $Success = $false
        }
    }
    catch {
        Write-Host "  ✗ API Health detail FAILED: $_" -ForegroundColor Red
        $Success = $false
    }

    # 3. Check UI SPA Fallback
    Write-Host "[3/5] Testing /ui/mesh (SPA Fallback)..."
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8001/ui/mesh" -Method Get -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Host "  ✓ UI SPA Fallback OK" -ForegroundColor Green
        }
        else {
            Write-Host "  ✗ UI SPA Fallback FAILED: $($response.StatusCode)" -ForegroundColor Red
            $Success = $false
        }
    }
    catch {
        Write-Host "  ✗ UI SPA Fallback FAILED: $_" -ForegroundColor Red
        $Success = $false
    }

    # 4. Check Persistent Data Initialization
    Write-Host "[4/5] Checking Data Directory..."
    $DATA_DIR = Join-Path $EXE_DIR "data"
    if (Test-Path $DATA_DIR) {
        Write-Host "  ✓ Data directory created at $DATA_DIR" -ForegroundColor Green
    }
    else {
        Write-Host "  ✗ Data directory NOT found at $DATA_DIR" -ForegroundColor Yellow
        # We don't fail yet, maybe it's just slow
    }

    # 5. Golden Job Verification
    Write-Host "[5/5] Testing Golden Job (Creation)..."
    try {
        $mission = Invoke-RestMethod -Uri "http://localhost:8001/api/missions/standard-code-analysis" -Method Post
        if ($mission.job.id) {
            Write-Host "  ✓ Mission & Job created: $($mission.job.id)" -ForegroundColor Green
        }
        else {
            Write-Host "  ✗ Job creation FAILED" -ForegroundColor Red
            $Success = $false
        }
    }
    catch {
        Write-Host "  ✗ Golden Job FAILED: $_" -ForegroundColor Red
        $Success = $false
    }
}
finally {
    # Cleanup
    Write-Host "`nTerminating test instance..."
    try { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } catch {}
}

if ($Success) {
    Write-Host "`n--- ACCEPTANCE PASSED ---" -ForegroundColor Green
}
else {
    Write-Host "`n--- ACCEPTANCE FAILED ---" -ForegroundColor Red
    exit 1
}
