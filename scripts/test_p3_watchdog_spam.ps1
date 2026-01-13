# P3.2: Watchdog Spam Test
# Tests handling of rapid file modification events

. "$PSScriptRoot\_helpers.ps1"

$testName = "test_p3_watchdog_spam"
$root = "runtime/tests"
$testDir = New-TestDir -Root $root -TestName $testName
$started = Get-Date
$stdout = Join-Path $testDir "stdout.log"

try {
    $ms = Measure-BlockMs {
        "=== P3.2: Watchdog Spam Test ===" | Out-File -FilePath $stdout -Encoding utf8
        "" | Out-File -FilePath $stdout -Append -Encoding utf8
        
        $jobId = "watchdog_spam_test_$(Get-Date -Format 'yyyyMMddHHmmss')"
        $jobFile = "data\webrelay_out\$jobId.job.json"
        
        # Create job file
        "[1/3] Creating job file..." | Out-File -FilePath $stdout -Append -Encoding utf8
        $job = @{
            job_id = $jobId
            kind = "list_files"
            payload = @{
                params = @{
                    root = "."
                    max_depth = 1
                }
            }
            metadata = @{
                test = "p3_watchdog_spam"
            }
        } | ConvertTo-Json -Depth 10
        
        $job | Set-Content $jobFile -Encoding UTF8
        
        # Spam: touch file 10 times rapidly
        "[2/3] Spamming file modifications (10x)..." | Out-File -FilePath $stdout -Append -Encoding utf8
        for ($i = 1; $i -le 10; $i++) {
            (Get-Item $jobFile).LastWriteTime = Get-Date
            Start-Sleep -Milliseconds 10
        }
        
        "  [OK] File modified 10 times" | Out-File -FilePath $stdout -Append -Encoding utf8
        
        # Wait for processing (deterministic)
        "[3/3] Waiting for job to process..." | Out-File -FilePath $stdout -Append -Encoding utf8
        $waitResult = Wait-Until `
            -Condition { Test-Path "data\webrelay_in\$jobId.result.json" } `
            -TimeoutSeconds 10 `
            -Label "Job processed"
        
        Assert-True -Expr $waitResult -Message "Job not processed"
        
        # Verify single processing
        $byJobId = Get-JobResultsByJobId -ResultsDir "data\webrelay_in"
        $jobResults = $byJobId[$jobId]
        
        Assert-True -Expr ($jobResults.Count -eq 1) -Message "Job processed $($jobResults.Count) times (expected 1)"
        "  [OK] Job processed exactly once" | Out-File -FilePath $stdout -Append -Encoding utf8
    }

    $metrics = @{
        job_id = $jobId
        modification_count = 10
        processed_exactly_once = $true
    }
    
    $res = New-TestResult -Test $testName -Pass $true -DurationMs $ms -Metrics $metrics -Artifacts @($stdout)
    
} catch {
    $ms = [int]((Get-Date) - $started).TotalMilliseconds
    $_ | Out-String | Out-File -FilePath $stdout -Append -Encoding utf8
    $res = New-TestResult -Test $testName -Pass $false -Status "FAIL" -DurationMs $ms -Message $_.Exception.Message -Artifacts @($stdout)
}

Write-TestReport -Result $res -TestDir $testDir -StdoutLogPath $stdout | Out-Null
$res
