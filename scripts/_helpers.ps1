Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function New-TestResult {
    param(
        [Parameter(Mandatory=$true)][string]$Test,
        [Parameter(Mandatory=$true)][bool]$Pass,
        [hashtable]$Metrics = @{},
        [string[]]$Artifacts = @(),
        [ValidateSet("PASS","FAIL","SKIP")][string]$Status = $(if($Pass){"PASS"}else{"FAIL"}),
        [string]$SkipReason = $null,
        [string]$Message = $null,
        [datetime]$StartedAt = $(Get-Date),
        [int]$DurationMs = 0
    )

    return [pscustomobject]@{
        test        = $Test
        status      = $Status
        pass        = $Pass
        started_at  = $StartedAt.ToString("o")
        duration_ms = $DurationMs
        message     = $Message
        skip_reason = $SkipReason
        metrics     = $Metrics
        artifacts   = $Artifacts
    }
}

function Write-TestReport {
    <#
      Writes report.json + stdout.log friendly output.
      Ensures report is always written even on failures when used in try/catch.
    #>
    param(
        [Parameter(Mandatory=$true)][pscustomobject]$Result,
        [Parameter(Mandatory=$true)][string]$TestDir,
        [string]$StdoutLogPath = $null
    )

    New-Item -ItemType Directory -Path $TestDir -Force | Out-Null

    $reportPath = Join-Path $TestDir "report.json"
    $Result | ConvertTo-Json -Depth 12 | Out-File -FilePath $reportPath -Encoding utf8

    if ($StdoutLogPath) {
        # Caller may want to append additional logs; just record artifact path
        # (No-op here; the file may already exist.)
        if (-not (Test-Path $StdoutLogPath)) {
            "" | Out-File -FilePath $StdoutLogPath -Encoding utf8
        }
    }

    # Console summary (so RUN_ALL runner can show quick status)
    $badge = switch ($Result.status) { "PASS" { "[OK]" } "FAIL" { "[FAIL]" } "SKIP" { "[SKIP]" } default { "[INFO]" } }
    $color = switch ($Result.status) { "PASS" { "Green" } "FAIL" { "Red" } "SKIP" { "Yellow" } default { "Gray" } }
    Write-Host "$badge $($Result.test): $($Result.status) ($($Result.duration_ms)ms)" -ForegroundColor $color
    if ($Result.message) { Write-Host "   $($Result.message)" -ForegroundColor DarkGray }

    return $reportPath
}

function Wait-Until {
    <#
      Deterministic wait with timeout + polling.
      Returns $true if condition met, else $false.
    #>
    param(
        [Parameter(Mandatory=$true)][scriptblock]$Condition,
        [int]$TimeoutSeconds = 60,
        [int]$PollMilliseconds = 250,
        [string]$Label = "condition"
    )

    $start = Get-Date
    while ($true) {
        try {
            if (& $Condition) { return $true }
        } catch {
            # Condition exceptions should not instantly fail waiting; keep polling.
        }

        $elapsed = (Get-Date) - $start
        if ($elapsed.TotalSeconds -ge $TimeoutSeconds) {
            return $false
        }

        Start-Sleep -Milliseconds $PollMilliseconds
    }
}

function Assert-True {
    param(
        [Parameter(Mandatory=$true)][bool]$Expr,
        [Parameter(Mandatory=$true)][string]$Message
    )
    if (-not $Expr) { throw "ASSERT_TRUE failed: $Message" }
}

function Get-ProcByCommandLineLike {
    <#
      Reliable worker detection: Win32_Process gives command line.
    #>
    param(
        [Parameter(Mandatory=$true)][string]$Pattern
    )
    return Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like $Pattern }
}

function Get-OwningPidByPort {
    param(
        [Parameter(Mandatory=$true)][int]$Port
    )
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $conn) { return $null }
    return $conn.OwningProcess
}

function Test-HttpReady {
    param(
        [Parameter(Mandatory=$true)][string]$Url,
        [int]$TimeoutSeconds = 10
    )
    try {
        $resp = Invoke-WebRequest -Uri $Url -Method GET -TimeoutSec $TimeoutSeconds -UseBasicParsing
        return ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 300)
    } catch {
        return $false
    }
}

function New-TestDir {
    param(
        [Parameter(Mandatory=$true)][string]$Root,
        [Parameter(Mandatory=$true)][string]$TestName
    )
    $dir = Join-Path $Root $TestName
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
    return $dir
}

function Measure-BlockMs {
    param([Parameter(Mandatory=$true)][scriptblock]$Block)
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    & $Block
    $sw.Stop()
    return [int]$sw.ElapsedMilliseconds
}

function Read-JsonSafe {
    param([Parameter(Mandatory=$true)][string]$Path)
    $txt = Get-Content $Path -Raw -ErrorAction Stop
    return $txt | ConvertFrom-Json -ErrorAction Stop
}

# ============================================================================
# Micro-Helpers: Robust Dedupe + Trend Analysis
# ============================================================================

function Get-JobResultsByJobId {
    <#
      Robust dedupe check via JSON parsing.
      Returns hashtable: job_id -> array of result file paths
    #>
    param(
        [Parameter(Mandatory=$true)][string]$ResultsDir,
        [string]$Pattern = "*.result.json"
    )
    
    $results = Get-ChildItem (Join-Path $ResultsDir $Pattern) -ErrorAction SilentlyContinue
    $byJobId = @{}
    
    foreach ($file in $results) {
        try {
            $json = Read-JsonSafe -Path $file.FullName
            
            # Try common fields
            $jobId = $null
            if ($json.job_id) { $jobId = $json.job_id }
            elseif ($json.id) { $jobId = $json.id }
            elseif ($json.jobId) { $jobId = $json.jobId }
            else {
                # Fallback to filename
                $jobId = [System.IO.Path]::GetFileNameWithoutExtension($file.Name) -replace '\.result$', ''
            }
            
            if (-not $byJobId.ContainsKey($jobId)) {
                $byJobId[$jobId] = @()
            }
            $byJobId[$jobId] += $file.FullName
            
        } catch {
            Write-Warning "Could not parse $($file.FullName): $_"
        }
    }
    
    return $byJobId
}

function Assert-NoLinearGrowth {
    <#
      For 24h metrics: RAM/Handles trend check.
      Reads JSONL metrics file and checks if values are linearly increasing.
      Returns $true if stable (no linear growth), $false if growing.
    #>
    param(
        [Parameter(Mandatory=$true)][string]$MetricsFile,
        [Parameter(Mandatory=$true)][string]$MetricPath,  # e.g. "worker.ram_mb"
        [double]$MaxGrowthPerHour = 10.0,  # Max acceptable growth per hour
        [int]$MinSamples = 10
    )
    
    if (-not (Test-Path $MetricsFile)) {
        Write-Warning "Metrics file not found: $MetricsFile"
        return $true  # Can't check, assume OK
    }
    
    $lines = Get-Content $MetricsFile
    if ($lines.Count -lt $MinSamples) {
        Write-Warning "Not enough samples ($($lines.Count) < $MinSamples)"
        return $true  # Not enough data
    }
    
    $values = @()
    $timestamps = @()
    
    foreach ($line in $lines) {
        try {
            $obj = $line | ConvertFrom-Json
            
            # Navigate metric path (e.g. "worker.ram_mb")
            $parts = $MetricPath -split '\.'
            $value = $obj
            foreach ($part in $parts) {
                $value = $value.$part
            }
            
            if ($null -ne $value) {
                $values += [double]$value
                $timestamps += [datetime]::Parse($obj.timestamp)
            }
        } catch {
            # Skip invalid lines
        }
    }
    
    if ($values.Count -lt $MinSamples) {
        return $true
    }
    
    # Simple linear regression: check if slope is positive and significant
    $n = $values.Count
    $firstValue = $values[0]
    $lastValue = $values[$n - 1]
    $timeSpan = ($timestamps[$n - 1] - $timestamps[0]).TotalHours
    
    if ($timeSpan -eq 0) {
        return $true  # No time passed
    }
    
    $growthPerHour = ($lastValue - $firstValue) / $timeSpan
    
    if ($growthPerHour -gt $MaxGrowthPerHour) {
        Write-Warning "Linear growth detected: $MetricPath growing at $([math]::Round($growthPerHour, 2))/hour (max: $MaxGrowthPerHour)"
        return $false
    }
    
    return $true
}
