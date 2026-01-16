# scripts/stop_ports.ps1
# Kills processes bound to the given TCP ports (Windows).
param(
    [int[]]$Ports = @(8001, 8787, 8788, 3001),
    [switch]$WhatIf
)

$ErrorActionPreference = "SilentlyContinue"

function Get-PidsForPort([int]$port) {
    $lines = netstat -ano | Select-String -Pattern "[:.]$port\s"
    if (-not $lines) { return @() }

    $pids = @()
    foreach ($l in $lines) {
        $parts = ($l.ToString() -split "\s+") | Where-Object { $_ -ne "" }
        # typical: TCP 0.0.0.0:8001 ... LISTENING 12345
        $found_pid = $parts[-1]
        if ($found_pid -match "^\d+$") { $pids += [int]$found_pid }
    }
    return $pids | Sort-Object -Unique
}

Write-Host "=== stop_ports.ps1 ==="
foreach ($p in $Ports) {
    $pids = Get-PidsForPort $p
    if ($pids.Count -eq 0) {
        Write-Host "[OK] Port $p: no listeners found"
        continue
    }

    foreach ($found_pid in $pids) {
        $proc = Get-Process -Id $found_pid -ErrorAction SilentlyContinue
        $name = if ($proc) { $proc.ProcessName } else { "unknown" }
        if ($WhatIf) {
            Write-Host "[WHATIF] Would kill PID $found_pid ($name) on port $p"
        }
        else {
            Write-Host "[KILL] Port $p -> PID $found_pid ($name)"
            Stop-Process -Id $found_pid -Force -ErrorAction SilentlyContinue
        }
    }
}
Write-Host "Done."