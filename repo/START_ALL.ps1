# Sheratan Production Startup Script
# Starts all services with health checks and heartbeat monitoring

param(
    [switch]$SkipChrome,
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"
$ROOT = $PSScriptRoot

Write-Host "╔═══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     Sheratan Production System Startup v2.0          ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# 0. Create directories
Write-Host "[0/6] Creating directories..." -ForegroundColor Yellow
@("runtime", "logs", "data\webrelay_out", "data\webrelay_in", "data\chrome_profile", "config") | ForEach-Object {
    if (!(Test-Path "$ROOT\$_")) {
        New-Item -ItemType Directory -Path "$ROOT\$_" -Force | Out-Null
    }
}
Write-Host "✅ Directories ready" -ForegroundColor Green

# 1. Start Chrome Debug Mode (if not skipped)
if (!$SkipChrome) {
    Write-Host "[1/6] Starting Chrome Debug Mode..." -ForegroundColor Yellow
    $chromePath = @(
        "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
        "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
    
    if ($chromePath) {
        Start-Process -FilePath $chromePath -ArgumentList @(
            "--remote-debugging-port=9222",
            "--user-data-dir=$ROOT\data\chrome_profile",
            "--no-first-run",
            "--no-default-browser-check",
            "https://chatgpt.com",
            "https://gemini.google.com"
        ) -WindowStyle Normal
        Start-Sleep -Seconds 3
        Write-Host "✅ Chrome Debug running on port 9222" -ForegroundColor Green
    }
    else {
        Write-Host "⚠️  Chrome not found - WebRelay may not work" -ForegroundColor Red
    }
}
else {
    Write-Host "[1/6] Skipping Chrome (--SkipChrome flag)" -ForegroundColor Gray
}

# 2. Start Core (with heartbeat)
Write-Host "[2/6] Starting Core API..." -ForegroundColor Yellow
$env:PYTHONPATH = $ROOT
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "`$env:PYTHONPATH='$ROOT'; cd '$ROOT\core'; python main.py"
) -WindowStyle Normal
Start-Sleep -Seconds 8

# Health check
try {
    $coreHealth = Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/jobs" -TimeoutSec 5
    Write-Host "✅ Core operational ($($coreHealth.status))" -ForegroundColor Green
}
catch {
    Write-Host "❌ Core health check FAILED" -ForegroundColor Red
    throw "Core startup failed"
}

# 3. Start Broker
Write-Host "[3/6] Starting Broker..." -ForegroundColor Yellow
$env:PYTHONPATH = $ROOT
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "`$env:PYTHONPATH='$ROOT'; python '$ROOT\hub\mesh\offgrid\broker\auction_api.py' --port 9000"
) -WindowStyle Normal
Start-Sleep -Seconds 3

try {
    $brokerHealth = Invoke-RestMethod -Uri "http://localhost:9000/health" -TimeoutSec 5
    Write-Host "✅ Broker operational" -ForegroundColor Green
}
catch {
    Write-Host "⚠️  Broker health check failed (non-critical)" -ForegroundColor Yellow
}

# 4. Start Node-A
Write-Host "[4/6] Starting Node-A Worker..." -ForegroundColor Yellow
$env:PYTHONPATH = $ROOT
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "`$env:PYTHONPATH='$ROOT'; `$env:SHERATAN_HOST_IP='127.0.0.1'; python '$ROOT\hub\mesh\offgrid\host\api_real.py' --port 8081 --node_id node-A --host 127.0.0.1"
),
Start-Sleep -Seconds 2

try {
    $nodeHealth = Invoke-RestMethod -Uri "http://localhost:8081/health" -TimeoutSec 5
    Write-Host "✅ Node-A operational" -ForegroundColor Green
}
catch {
    Write-Host "⚠️  Node-A health check failed (non-critical)" -ForegroundColor Yellow
}

# 5. Start WebRelay
Write-Host "[5/6] Starting WebRelay..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$ROOT\external\webrelay-v2'; npm start"
) -WindowStyle Normal
Start-Sleep -Seconds 5

try {
    $relayHealth = Invoke-RestMethod -Uri "http://localhost:3000/health" -TimeoutSec 5
    Write-Host "✅ WebRelay operational" -ForegroundColor Green
}
catch {
    Write-Host "❌ WebRelay health check FAILED" -ForegroundColor Red
    throw "WebRelay startup failed"
}

# 6. Start Dashboard
Write-Host "[6/6] Starting Dashboard..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$ROOT\hub\ui'; npx http-server -p 3001"
) -WindowStyle Normal
Start-Sleep -Seconds 3

try {
    Invoke-WebRequest -Uri "http://localhost:3001" -TimeoutSec 5 -UseBasicParsing | Out-Null
    Write-Host "✅ Dashboard operational on port 3001" -ForegroundColor Green
}
catch {
    Write-Host "⚠️  Dashboard health check failed (non-critical)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║          Sheratan System is OPERATIONAL               ║" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "Services:" -ForegroundColor Cyan
Write-Host "  • Chrome Debug:    port 9222" -ForegroundColor White
Write-Host "  • Core API:        http://localhost:8001" -ForegroundColor White
Write-Host "  • Broker:          http://localhost:9000" -ForegroundColor White
Write-Host "  • Node-A Worker:   http://localhost:8081" -ForegroundColor White
Write-Host "  • WebRelay:        http://localhost:3000" -ForegroundColor White
Write-Host "  • Dashboard:       http://localhost:3001" -ForegroundColor White
Write-Host ""
Write-Host "Monitoring:" -ForegroundColor Cyan
Write-Host "  • Service Status:  http://localhost:8001/api/system/services" -ForegroundColor White
Write-Host "  • Dashboard UI:    http://localhost:3001" -ForegroundColor White
Write-Host ""

# Verify heartbeats
Write-Host "Verifying heartbeats..." -ForegroundColor Yellow
Start-Sleep -Seconds 15
try {
    $services = (Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/system/services" -TimeoutSec 5).services
    
    Write-Host ""
    Write-Host "Heartbeat Status:" -ForegroundColor Cyan
    foreach ($svc in $services) {
        $status = if ($svc.alive) { "🟢" } else { "🔴" }
        $color = if ($svc.alive) { "Green" } else { "Red" }
        Write-Host "  $status $($svc.name): $($svc.seconds_since_ping)s ago" -ForegroundColor $color
    }
    
    $offline = $services | Where-Object { !$_.alive }
    if ($offline) {
        Write-Host ""
        Write-Host "⚠️  WARNING: Some services not sending heartbeats" -ForegroundColor Yellow
    }
    else {
        Write-Host ""
        Write-Host "✅ All monitored services sending heartbeats!" -ForegroundColor Green
    }
}
catch {
    Write-Host "⚠️  Could not verify heartbeats (service may still be starting)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "System ready. Opening dashboard..." -ForegroundColor Green
Start-Sleep -Seconds 2
Start-Process "http://localhost:3001"
