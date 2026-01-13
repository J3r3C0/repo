# P1.1: Worker Kill During Job Burst Test
# Tests worker crash recovery and job completion

. "$PSScriptRoot\_helpers.ps1"

$testName = "test_p1_worker_kill"
$root = "runtime/tests"
$testDir = New-TestDir -Root $root -TestName $testName
$started = Get-Date
$stdout = Join-Path $testDir "stdout.log"

try {
    $ms = Measure-BlockMs {
        "=== P1.1: Worker Kill Test ===" | Out-File -FilePath $stdout -Encoding utf8
        "" | Out-File -FilePath $stdout -Append -Encoding utf8
        
        $jobCount = 50
        $jobIds = @()
        
        # Submit jobs
        "[1/5] Submitting $jobCount jobs..." | Out-File -FilePath $stdout -Append -Encoding utf8
        for ($i = 1; $i -le $jobCount; $i++) {
            $jobId = [guid]::NewGuid().ToString()
            $jobIds += $jobId
            
            $job = @{
                job_id = $jobId
                kind = "list_files"
                payload = @{
                    params = @{
                        root = "."
                        max_depth = 2
                    }
                }
                metadata = @{
                    test = "p1_worker_kill"
                    job_number = $i
                }
            } | ConvertTo-Json -Depth 10
            
            $jobFile = "data\webrelay_out\$jobId.job.json"
            $job | Out-File $jobFile -Encoding UTF8
            
            Start-Sleep -Milliseconds 50
        }
        
        "  [OK] $jobCount jobs submitted" | Out-File -FilePath $stdout -Append -Encoding utf8
        
        # Wait until at least 10 processed (deterministic)
        "[2/5] Waiting for at least 10 jobs to process..." | Out-File -FilePath $stdout -Append -Encoding utf8
        $waitResult = Wait-Until `
            -Condition { (Get-ChildItem "data\webrelay_in\*.result.json" -ErrorAction SilentlyContinue).Count -ge 10 } `
            -TimeoutSeconds 30 `
            -Label "At least 10 jobs processed"
        
        Assert-True -Expr $waitResult -Message "Timeout waiting for initial 10 jobs to process"
        
        $processedBeforeKill = (Get-ChildItem "data\webrelay_in\*.result.json" -ErrorAction SilentlyContinue).Count
        "  Jobs processed before kill: $processedBeforeKill" | Out-File -FilePath $stdout -Append -Encoding utf8
        
        # Kill worker
        "[3/5] Killing worker process..." | Out-File -FilePath $stdout -Append -Encoding utf8
        $workers = Get-ProcByCommandLineLike -Pattern "*worker_loop.py*"
        Assert-True -Expr ($null -ne $workers) -Message "Worker process not found"
        
        $workerPid = $workers[0].ProcessId
        Stop-Process -Id $workerPid -Force
        "  [OK] Worker killed (PID: $workerPid)" | Out-File -FilePath $stdout -Append -Encoding utf8
        
        Start-Sleep -Seconds 2
        
        # Restart worker
        "[4/5] Restarting worker..." | Out-File -FilePath $stdout -Append -Encoding utf8
        $workerJob = Start-Job -ScriptBlock {
            Set-Location "c:\sauber_main\worker"
            python worker_loop.py
        }
        
        Start-Sleep -Seconds 3
        "  [OK] Worker restarted" | Out-File -FilePath $stdout -Append -Encoding utf8
        
        # Wait for all jobs to complete (deterministic)
        "[5/5] Waiting for all $jobCount jobs to complete..." | Out-File -FilePath $stdout -Append -Encoding utf8
        $waitResult = Wait-Until `
            -Condition { (Get-ChildItem "data\webrelay_in\*.result.json" -ErrorAction SilentlyContinue).Count -ge $jobCount } `
            -TimeoutSeconds 60 `
            -Label "All $jobCount jobs completed"
        
        Assert-True -Expr $waitResult -Message "Timeout waiting for all jobs to complete"
        
        # Verify results using robust dedupe check
        "" | Out-File -FilePath $stdout -Append -Encoding utf8
        "Verifying results..." | Out-File -FilePath $stdout -Append -Encoding utf8
        
        $byJobId = Get-JobResultsByJobId -ResultsDir "data\webrelay_in"
        $duplicates = $byJobId.GetEnumerator() | Where-Object { $_.Value.Count -gt 1 }
        
        Assert-True -Expr ($duplicates.Count -eq 0) -Message "Found $($duplicates.Count) duplicate job(s)"
        "  [OK] No duplicates" | Out-File -FilePath $stdout -Append -Encoding utf8
        
        Assert-True -Expr ($byJobId.Count -eq $jobCount) -Message "Expected $jobCount results, got $($byJobId.Count)"
        "  [OK] All $jobCount jobs completed" | Out-File -FilePath $stdout -Append -Encoding utf8
    }

    $metrics = @{
        jobs_submitted = $jobCount
        jobs_completed = $byJobId.Count
        duplicates = $duplicates.Count
        processed_before_kill = $processedBeforeKill
    }
    
    $res = New-TestResult -Test $testName -Pass $true -DurationMs $ms -Metrics $metrics -Artifacts @($stdout)
    
} catch {
    $ms = [int]((Get-Date) - $started).TotalMilliseconds
    $_ | Out-String | Out-File -FilePath $stdout -Append -Encoding utf8
    $res = New-TestResult -Test $testName -Pass $false -Status "FAIL" -DurationMs $ms -Message $_.Exception.Message -Artifacts @($stdout)
}

Write-TestReport -Result $res -TestDir $testDir -StdoutLogPath $stdout | Out-Null
$res
