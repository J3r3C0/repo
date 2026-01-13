# Test Helper Functions for Burn-In Suite
# Provides consistent Wait-Until, Test Reporting, and Utilities

# ============================================================================
# Wait-Until: Deterministic waiting with timeout and condition
# ============================================================================

function Wait-Until {
    param(
        [Parameter(Mandatory=$true)]
        [ScriptBlock]$Condition,
        
        [Parameter(Mandatory=$true)]
        [string]$Description,
        
        [int]$TimeoutSeconds = 60,
        [int]$CheckIntervalMs = 500
    )
    
    $startTime = Get-Date
    $elapsed = 0
    
    Write-Host "Waiting for: $Description (timeout: ${TimeoutSeconds}s)" -ForegroundColor Gray
    
    while ($elapsed -lt $TimeoutSeconds) {
        if (& $Condition) {
            $duration = ((Get-Date) - $startTime).TotalSeconds
            Write-Host "  [OK] Condition met after $([math]::Round($duration, 2))s" -ForegroundColor Green
            return $true
        }
        
        Start-Sleep -Milliseconds $CheckIntervalMs
        $elapsed = ((Get-Date) - $startTime).TotalSeconds
    }
    
    Write-Host "  [TIMEOUT] Condition not met after ${TimeoutSeconds}s" -ForegroundColor Red
    return $false
}

# ============================================================================
# Write-TestReport: Consistent test result output
# ============================================================================

function Write-TestReport {
    param(
        [Parameter(Mandatory=$true)]
        [string]$TestName,
        
        [Parameter(Mandatory=$true)]
        [bool]$Pass,
        
        [Parameter(Mandatory=$true)]
        [datetime]$StartTime,
        
        [hashtable]$Metrics = @{},
        [string[]]$Artifacts = @(),
        [string]$FailureReason = "",
        [string]$OutputDir = "runtime/tests"
    )
    
    $endTime = Get-Date
    $duration = ($endTime - $StartTime).TotalMilliseconds
    
    # Create test-specific directory
    $testDir = Join-Path $OutputDir $TestName
    if (-not (Test-Path $testDir)) {
        New-Item -ItemType Directory -Path $testDir -Force | Out-Null
    }
    
    # Build report object
    $report = @{
        test = $TestName
        started_at = $StartTime.ToString("o")
        ended_at = $endTime.ToString("o")
        duration_ms = [int]$duration
        pass = $Pass
        metrics = $Metrics
        artifacts = $Artifacts
    }
    
    if (-not $Pass -and $FailureReason) {
        $report.failure_reason = $FailureReason
    }
    
    # Write JSON report
    $reportPath = Join-Path $testDir "report.json"
    $report | ConvertTo-Json -Depth 10 | Out-File $reportPath -Encoding UTF8
    
    # Display summary
    $status = if ($Pass) { "[PASS]" } else { "[FAIL]" }
    $color = if ($Pass) { "Green" } else { "Red" }
    
    Write-Host ""
    Write-Host "=== Test Report: $TestName ===" -ForegroundColor Cyan
    Write-Host "Status: $status" -ForegroundColor $color
    Write-Host "Duration: $([math]::Round($duration / 1000, 2))s" -ForegroundColor Gray
    
    if ($Metrics.Count -gt 0) {
        Write-Host "Metrics:" -ForegroundColor Gray
        $Metrics.GetEnumerator() | ForEach-Object {
            Write-Host "  $($_.Key): $($_.Value)" -ForegroundColor Gray
        }
    }
    
    if (-not $Pass) {
        Write-Host "Failure: $FailureReason" -ForegroundColor Red
    }
    
    Write-Host "Report: $reportPath" -ForegroundColor Gray
    Write-Host ""
    
    # Return report object for aggregation
    return $report
}

# ============================================================================
# Get-JobIdFromResult: Extract job_id from result JSON
# ============================================================================

function Get-JobIdFromResult {
    param(
        [Parameter(Mandatory=$true)]
        [string]$ResultFile
    )
    
    try {
        $content = Get-Content $ResultFile -Raw | ConvertFrom-Json
        
        # Try common fields
        if ($content.job_id) { return $content.job_id }
        if ($content.id) { return $content.id }
        if ($content.jobId) { return $content.jobId }
        
        # Fallback to filename
        return [System.IO.Path]::GetFileNameWithoutExtension($ResultFile) -replace '\.result$', ''
    }
    catch {
        Write-Host "Warning: Could not parse job_id from $ResultFile" -ForegroundColor Yellow
        return $null
    }
}

# ============================================================================
# Test-Dedupe: Check for duplicate job processing
# ============================================================================

function Test-Dedupe {
    param(
        [Parameter(Mandatory=$true)]
        [string]$ResultsDir,
        
        [string]$Pattern = "*.result.json"
    )
    
    $results = Get-ChildItem (Join-Path $ResultsDir $Pattern) -ErrorAction SilentlyContinue
    
    if (-not $results) {
        return @{
            total = 0
            unique = 0
            duplicates = @()
        }
    }
    
    # Extract job_ids from JSON content
    $jobIds = @()
    foreach ($result in $results) {
        $jobId = Get-JobIdFromResult $result.FullName
        if ($jobId) {
            $jobIds += $jobId
        }
    }
    
    # Group and find duplicates
    $grouped = $jobIds | Group-Object
    $duplicates = $grouped | Where-Object { $_.Count -gt 1 }
    
    return @{
        total = $results.Count
        unique = $grouped.Count
        duplicates = $duplicates | ForEach-Object { 
            @{ job_id = $_.Name; count = $_.Count }
        }
    }
}

# ============================================================================
# Get-WorkerProcess: Reliable worker process detection
# ============================================================================

function Get-WorkerProcess {
    $workers = Get-CimInstance Win32_Process | Where-Object {
        $_.CommandLine -like "*worker_loop.py*" -and $_.CommandLine -notlike "*Get-CimInstance*"
    }
    
    return $workers
}

# ============================================================================
# Test-PortListening: Check if port is listening with health check
# ============================================================================

function Test-PortListening {
    param(
        [Parameter(Mandatory=$true)]
        [int]$Port,
        
        [string]$HealthEndpoint = "",
        [int]$TimeoutSeconds = 5
    )
    
    # Check port
    $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    
    if (-not $connection) {
        return @{ listening = $false; healthy = $false }
    }
    
    # If health endpoint provided, check it
    if ($HealthEndpoint) {
        try {
            $response = Invoke-RestMethod -Uri $HealthEndpoint -Method GET -TimeoutSec $TimeoutSeconds -ErrorAction Stop
            return @{ listening = $true; healthy = $true; response = $response }
        }
        catch {
            return @{ listening = $true; healthy = $false; error = $_.Exception.Message }
        }
    }
    
    return @{ listening = $true; healthy = $null }
}

# ============================================================================
# Get-StaleClaims: Find stale .claimed files with TTL check
# ============================================================================

function Get-StaleClaims {
    param(
        [Parameter(Mandatory=$true)]
        [string]$JobDir,
        
        [int]$TtlSeconds = 300  # 5 minutes default
    )
    
    $claims = Get-ChildItem (Join-Path $JobDir "*.claimed") -ErrorAction SilentlyContinue
    
    if (-not $claims) {
        return @{
            total = 0
            stale = @()
            fresh = @()
        }
    }
    
    $now = Get-Date
    $stale = @()
    $fresh = @()
    
    foreach ($claim in $claims) {
        $age = ($now - $claim.LastWriteTime).TotalSeconds
        
        if ($age -gt $TtlSeconds) {
            $stale += @{
                file = $claim.Name
                age_seconds = [int]$age
            }
        } else {
            $fresh += $claim.Name
        }
    }
    
    return @{
        total = $claims.Count
        stale = $stale
        fresh = $fresh
    }
}

# ============================================================================
# Write-TestMetadata: Write test run metadata
# ============================================================================

function Write-TestMetadata {
    param(
        [string]$OutputDir = "runtime/tests",
        [hashtable]$Config = @{}
    )
    
    $metaDir = $OutputDir
    if (-not (Test-Path $metaDir)) {
        New-Item -ItemType Directory -Path $metaDir -Force | Out-Null
    }
    
    # Get git commit if available
    $gitCommit = ""
    try {
        $gitCommit = git rev-parse HEAD 2>$null
    } catch {}
    
    # Get Python version
    $pythonVersion = ""
    try {
        $pythonVersion = python --version 2>&1
    } catch {}
    
    $metadata = @{
        timestamp = (Get-Date).ToString("o")
        machine = @{
            hostname = $env:COMPUTERNAME
            os = [System.Environment]::OSVersion.VersionString
            python_version = $pythonVersion
        }
        git_commit = $gitCommit
        config = $Config
    }
    
    $metaPath = Join-Path $metaDir "_meta.json"
    $metadata | ConvertTo-Json -Depth 10 | Out-File $metaPath -Encoding UTF8
    
    Write-Host "Test metadata written to: $metaPath" -ForegroundColor Gray
    
    return $metadata
}

# ============================================================================
# Export functions
# ============================================================================

Export-ModuleMember -Function @(
    'Wait-Until',
    'Write-TestReport',
    'Get-JobIdFromResult',
    'Test-Dedupe',
    'Get-WorkerProcess',
    'Test-PortListening',
    'Get-StaleClaims',
    'Write-TestMetadata'
)
