# scripts/start_core.ps1
# Golden path starter for Sheratan Core v2 (Windows PowerShell).
param(
    [string]$ListenHost = "0.0.0.0",
    [int]$Port = 8001,
    [switch]$KillPort,
    [switch]$UseUvicorn,          # default is python -u core/main.py
    [string]$BaseDir = ""         # optional explicit repo root
)

$ErrorActionPreference = "Stop"

function Resolve-RepoRoot {
    if ($BaseDir -and (Test-Path $BaseDir)) { return (Resolve-Path $BaseDir).Path }
    return (Resolve-Path "$PSScriptRoot\..").Path
}

$root = Resolve-RepoRoot
Set-Location $root

Write-Host "=== start_core.ps1 ==="
Write-Host "Repo: $root"
Write-Host "Host: $ListenHost  Port: $Port"

if ($KillPort) {
    $stop = Join-Path $root "scripts\stop_ports.ps1"
    if (Test-Path $stop) {
        & $stop -Ports @($Port)
    }
    else {
        Write-Host "[WARN] scripts/stop_ports.ps1 not found, using netstat fallback"
        $hits = netstat -ano | Select-String -Pattern "[:.]$Port\s"
        if ($hits) { Write-Host "[WARN] Port $Port appears in use; consider freeing it manually." }
    }
}

if ($UseUvicorn) {
    # Uvicorn path
    $env:PYTHONPATH = $root
    Write-Host "[RUN] python -m uvicorn core.main:app --host $ListenHost --port $Port"
    python -m uvicorn core.main:app --host $ListenHost --port $Port
}
else {
    # Direct run path (recommended if your core/main.py already boots uvicorn internally)
    Write-Host "[RUN] python -u core/main.py"
    python -u core/main.py
}