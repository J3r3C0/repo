# P0: State Display Test
# Tests state machine transitions and display correctness

. "$PSScriptRoot\_helpers.ps1"

$testName = "test_p0_state_display"
$root = "runtime/tests"
$testDir = New-TestDir -Root $root -TestName $testName
$started = Get-Date
$stdout = Join-Path $testDir "stdout.log"

try {
    $ms = Measure-BlockMs {
        # Get initial state
        "=== P0: State Display Test ===" | Out-File -FilePath $stdout -Encoding utf8
        "" | Out-File -FilePath $stdout -Append -Encoding utf8
        
        "[1/4] Reading initial state..." | Out-File -FilePath $stdout -Append -Encoding utf8
        $stateBefore = Invoke-RestMethod -Uri "http://localhost:8001/api/system/state" -Method GET
        $transitionsBefore = (Get-Content "logs/state_transitions.jsonl" -ErrorAction SilentlyContinue | Measure-Object).Count
        
        "  Initial state: $($stateBefore.state)" | Out-File -FilePath $stdout -Append -Encoding utf8
        "  Transitions logged: $transitionsBefore" | Out-File -FilePath $stdout -Append -Encoding utf8
        
        # Transition 1: PAUSED → OPERATIONAL
        "[2/4] Triggering transition: PAUSED -> OPERATIONAL..." | Out-File -FilePath $stdout -Append -Encoding utf8
        $transition1 = Invoke-RestMethod -Uri "http://localhost:8001/api/system/state/transition" `
            -Method POST `
            -Headers @{"Content-Type"="application/json"} `
            -Body '{"state": "OPERATIONAL", "reason": "P0 test transition"}'
        
        Start-Sleep -Seconds 1
        
        # Verify OPERATIONAL
        $stateRunning = Invoke-RestMethod -Uri "http://localhost:8001/api/system/state" -Method GET
        Assert-True -Expr ($stateRunning.state -eq "OPERATIONAL") -Message "State should be OPERATIONAL, got: $($stateRunning.state)"
        "  [OK] State is OPERATIONAL" | Out-File -FilePath $stdout -Append -Encoding utf8
        
        # Transition 2: OPERATIONAL → PAUSED
        "[3/4] Triggering transition: OPERATIONAL -> PAUSED..." | Out-File -FilePath $stdout -Append -Encoding utf8
        $transition2 = Invoke-RestMethod -Uri "http://localhost:8001/api/system/state/transition" `
            -Method POST `
            -Headers @{"Content-Type"="application/json"} `
            -Body '{"state": "PAUSED", "reason": "P0 test transition back"}'
        
        Start-Sleep -Seconds 1
        
        # Get final state
        "[4/4] Verifying final state..." | Out-File -FilePath $stdout -Append -Encoding utf8
        $stateAfter = Invoke-RestMethod -Uri "http://localhost:8001/api/system/state" -Method GET
        $transitionsAfter = (Get-Content "logs/state_transitions.jsonl" -ErrorAction SilentlyContinue | Measure-Object).Count
        
        # Verify state
        Assert-True -Expr ($stateAfter.state -eq "PAUSED") -Message "State should be PAUSED, got: $($stateAfter.state)"
        "  [OK] State is PAUSED" | Out-File -FilePath $stdout -Append -Encoding utf8
        
        # Verify transition count
        $expectedTransitions = $transitionsBefore + 2
        Assert-True -Expr ($transitionsAfter -eq $expectedTransitions) -Message "Expected $expectedTransitions transitions, got $transitionsAfter"
        "  [OK] Transition count correct ($transitionsAfter)" | Out-File -FilePath $stdout -Append -Encoding utf8
    }

    $metrics = @{
        transitions_before = if ($null -ne $transitionsBefore) { $transitionsBefore } else { 0 }
        transitions_after = if ($null -ne $transitionsAfter) { $transitionsAfter } else { 0 }
        transitions_added = if ($null -ne $transitionsBefore -and $null -ne $transitionsAfter) { $transitionsAfter - $transitionsBefore } else { 0 }
    }
    
    $res = New-TestResult -Test $testName -Pass $true -DurationMs $ms -Metrics $metrics -Artifacts @($stdout)
    
} catch {
    $ms = [int]((Get-Date) - $started).TotalMilliseconds
    $_ | Out-String | Out-File -FilePath $stdout -Append -Encoding utf8
    $res = New-TestResult -Test $testName -Pass $false -Status "FAIL" -DurationMs $ms -Message $_.Exception.Message -Artifacts @($stdout)
}

Write-TestReport -Result $res -TestDir $testDir -StdoutLogPath $stdout | Out-Null
$res
