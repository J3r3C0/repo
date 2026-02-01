# scripts/ops_status.ps1
# Sheratan Operations Status Utility (C1)

$baseUrl = "http://localhost:8001/api/system"

function Show-Header($text) {
    Write-Host "`n=== $text ===" -ForegroundColor Cyan
}

try {
    # 1. Fetch Health
    $health = Invoke-RestMethod -Uri "$baseUrl/health" -ErrorAction Stop
    
    Clear-Host
    Write-Host "Sheratan Ops Status - $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor White -BackgroundColor Blue
    
    $statusColor = if ($health.status -eq "OK") { "Green" } else { "Yellow" }
    Write-Host "Overall Status: " -NoNewline
    Write-Host "$($health.status)" -ForegroundColor $statusColor
    Write-Host "Version:        $($health.version)"
    Write-Host "DB Health:      " -NoNewline
    Write-Host "$($health.db)" -ForegroundColor (if ($health.db -eq "OK") { "Green" } else { "Red" })
    
    Show-Header "Queue & Capacity"
    Write-Host "Pending Jobs:   $($health.queue.depth) / $($health.queue.max)"
    Write-Host "Inflight:       $($health.queue.inflight) / $($health.queue.max_inflight)"
    
    Show-Header "Service Mesh"
    foreach ($service in $health.services.PSObject.Properties) {
        $color = if ($service.Value -eq "active") { "Green" } else { "Red" }
        Write-Host "$($service.Name.PadRight(15)): " -NoNewline
        Write-Host "$($service.Value)" -ForegroundColor $color
    }
    
    # 2. Fetch Metrics
    $metrics = Invoke-RestMethod -Uri "$baseUrl/metrics"
    
    Show-Header "Performance & Reliability (B2/B3)"
    Write-Host "Idempotency Hits:    $($metrics.idempotency.hits)"
    Write-Host "Collisions Detected: $($metrics.idempotency.collisions)" -ForegroundColor (if ($metrics.idempotency.collisions -gt 0) { "Yellow" } else { "Gray" })
    Write-Host "Integrity Failures:  $($metrics.integrity.failures)" -ForegroundColor (if ($metrics.integrity.failures -gt 0) { "Red" } else { "Gray" })
    Write-Host "Hash Writes:         $($metrics.integrity.hash_writes)"
    
    Show-Header "System resources"
    Write-Host "Uptime:         $($metrics.uptime_sec)s"
    Write-Host "CPU Usage:      $($metrics.process.cpu_pct)%"
    Write-Host "Memory:         $([math]::Round($metrics.process.mem_mb, 2)) MB"

}
catch {
    Write-Host "ERROR: Could not fetch status from Sheratan Core." -ForegroundColor Red
    Write-Host "Ensure the system is running on $baseUrl"
    Write-Host $_.Exception.Message -ForegroundColor Gray
}

Write-Host "`n[Auto-refresh in 5s ... CTRL+C to stop]" -ForegroundColor DarkGray
