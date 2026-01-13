# 24h Burn-In Monitoring Script
# Collects metrics every 5 minutes for long-term stability analysis

param(
    [int]$IntervalSeconds = 300,  # 5 minutes
    [string]$OutputFile = "runtime/tests/24h_metrics.jsonl"
)

Import-Module "$PSScriptRoot\TestHelpers.psm1" -Force

Write-Host "=== 24h Burn-In Monitoring ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Interval: $IntervalSeconds seconds" -ForegroundColor Gray
Write-Host "Output: $OutputFile" -ForegroundColor Gray
Write-Host "Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host ""

# Create output directory
$outputDir = Split-Path $OutputFile -Parent
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

# Initialize last line number for lock timeout counting
$lastLockTimeoutLine = 0

# Monitoring loop
$iteration = 0

while ($true) {
    $iteration++
    $timestamp = Get-Date -Format "o"
    
    Write-Host "[$timestamp] Collecting metrics (iteration $iteration)..." -ForegroundColor Gray
    
    try {
        # Worker metrics
        $workers = Get-WorkerProcess
        $workerMetrics = @{
            running = $workers.Count -gt 0
            pid = if ($workers) { $workers[0].ProcessId } else { $null }
            ram_mb = if ($workers) { [math]::Round($workers[0].WorkingSet64 / 1MB, 2) } else { 0 }
            handles = if ($workers) { $workers[0].HandleCount } else { 0 }
            cpu_total_seconds = if ($workers) { [math]::Round($workers[0].CPU, 2) } else { 0 }
        }
        
        # Filesystem metrics
        $jobsPending = (Get-ChildItem "data\webrelay_out\*.job.json" -ErrorAction SilentlyContinue).Count
        $jobsClaimed = (Get-ChildItem "data\webrelay_out\*.claimed" -ErrorAction SilentlyContinue).Count
        $jobsCompleted = (Get-ChildItem "data\webrelay_in\*.result.json" -ErrorAction SilentlyContinue).Count
        $failedReports = (Get-ChildItem "data\failed_reports\*.txt" -ErrorAction SilentlyContinue).Count
        
        # Stale claims check
        $staleResult = Get-StaleClaims -JobDir "data\webrelay_out" -TtlSeconds 300
        
        # Lock timeouts (count new ones since last check)
        $lockTimeouts = 0
        if (Test-Path "logs\state_transitions.jsonl") {
            $allLines = Get-Content "logs\state_transitions.jsonl"
            $lockTimeouts = ($allLines | Select-String "timeout" -SimpleMatch | 
                            Select-Object -Skip $lastLockTimeoutLine).Count
            $lastLockTimeoutLine = ($allLines | Select-String "timeout" -SimpleMatch).Count
        }
        
        # Core API health
        $coreHealth = Test-PortListening -Port 8001 -HealthEndpoint "http://localhost:8001/api/system/state"
        
        # WebRelay health
        $webrelayHealth = Test-PortListening -Port 3001 -HealthEndpoint "http://localhost:3001/api/health"
        
        # Build metrics object
        $metrics = @{
            timestamp = $timestamp
            iteration = $iteration
            worker = $workerMetrics
            filesystem = @{
                jobs_pending = $jobsPending
                jobs_claimed = $jobsClaimed
                jobs_completed = $jobsCompleted
                failed_reports = $failedReports
                stale_claims = $staleResult.stale.Count
            }
            services = @{
                core_healthy = $coreHealth.healthy
                webrelay_healthy = $webrelayHealth.healthy
            }
            lock_timeouts_interval = $lockTimeouts
        }
        
        # Write to JSONL
        $metrics | ConvertTo-Json -Compress | Out-File -Append $OutputFile -Encoding UTF8
        
        # Display summary
        Write-Host "  Worker: RAM=$($workerMetrics.ram_mb)MB, Handles=$($workerMetrics.handles)" -ForegroundColor Gray
        Write-Host "  Jobs: Pending=$jobsPending, Claimed=$jobsClaimed, Completed=$jobsCompleted" -ForegroundColor Gray
        Write-Host "  Stale claims: $($staleResult.stale.Count)" -ForegroundColor $(if ($staleResult.stale.Count -gt 0) { "Yellow" } else { "Gray" })
        Write-Host "  Lock timeouts (interval): $lockTimeouts" -ForegroundColor $(if ($lockTimeouts -gt 0) { "Yellow" } else { "Gray" })
        
    } catch {
        Write-Host "  [ERROR] $($_.Exception.Message)" -ForegroundColor Red
    }
    
    # Wait for next interval
    Start-Sleep -Seconds $IntervalSeconds
}
