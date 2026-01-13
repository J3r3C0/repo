# P3.1: Partial Write Test
# Tests handling of incomplete/partial file writes

. "$PSScriptRoot\_helpers.ps1"

$testName = "test_p3_partial_write"
$root = "runtime/tests"
$testDir = New-TestDir -Root $root -TestName $testName
$started = Get-Date
$stdout = Join-Path $testDir "stdout.log"

try {
    $ms = Measure-BlockMs {
        "=== P3.1: Partial Write Test ===" | Out-File -FilePath $stdout -Encoding utf8
        "" | Out-File -FilePath $stdout -Append -Encoding utf8
        
        $jobId = "partial_write_test_$(Get-Date -Format 'yyyyMMddHHmmss')"
        $jobFile = "data\webrelay_out\$jobId.job.json"
        
        # Step 1: Create empty file
        "[1/4] Creating empty file..." | Out-File -FilePath $stdout -Append -Encoding utf8
        "" | Set-Content $jobFile -NoNewline -Encoding UTF8
        Start-Sleep -Milliseconds 200
        
        # Step 2: Write half JSON (invalid)
        "[2/4] Writing partial (invalid) JSON..." | Out-File -FilePath $stdout -Append -Encoding utf8
        $partialJson = '{"job_id":"' + $jobId + '","kind":"list_files"'
        $partialJson | Set-Content $jobFile -NoNewline -Encoding UTF8
        Start-Sleep -Milliseconds 500
        
        # Check if worker tried to process (should not)
        $earlyResult = Get-ChildItem "data\webrelay_in\$jobId.result.json" -ErrorAction SilentlyContinue
        if ($earlyResult) {
            "  [WARN] Worker processed partial JSON (unexpected)" | Out-File -FilePath $stdout -Append -Encoding utf8
        } else {
            "  [OK] Worker did not process partial JSON" | Out-File -FilePath $stdout -Append -Encoding utf8
        }
        
        # Step 3: Complete JSON
        "[3/4] Completing JSON..." | Out-File -FilePath $stdout -Append -Encoding utf8
        $completeJson = @{
            job_id = $jobId
            kind = "list_files"
            payload = @{
                params = @{
                    root = "."
                    max_depth = 1
                }
            }
            metadata = @{
                test = "p3_partial_write"
            }
        } | ConvertTo-Json -Depth 10
        
        $completeJson | Set-Content $jobFile -NoNewline -Encoding UTF8
        
        # Step 4: Wait for processing (deterministic)
        "[4/4] Waiting for job to process..." | Out-File -FilePath $stdout -Append -Encoding utf8
        $waitResult = Wait-Until `
            -Condition { Test-Path "data\webrelay_in\$jobId.result.json" } `
            -TimeoutSeconds 10 `
            -Label "Job processed after complete JSON"
        
        Assert-True -Expr $waitResult -Message "Job not processed after completing JSON"
        "  [OK] Job processed successfully" | Out-File -FilePath $stdout -Append -Encoding utf8
        
        # Verify single processing
        $byJobId = Get-JobResultsByJobId -ResultsDir "data\webrelay_in"
        $jobResults = $byJobId[$jobId]
        
        Assert-True -Expr ($jobResults.Count -eq 1) -Message "Job processed $($jobResults.Count) times (expected 1)"
        "  [OK] Job processed exactly once" | Out-File -FilePath $stdout -Append -Encoding utf8
    }

    $metrics = @{
        job_id = $jobId
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
