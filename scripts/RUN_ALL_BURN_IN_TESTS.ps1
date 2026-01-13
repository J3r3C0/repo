param(
    [switch]$EnableMultiWorker = $false
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. "$PSScriptRoot\_helpers.ps1"
. "$PSScriptRoot\_runner_policy.ps1"

Write-Host "=== Phase 1 Burn-In Test Suite ===" -ForegroundColor Cyan
Write-Host ""

$config = Get-RunnerConfig -EnableMultiWorker:$EnableMultiWorker
Write-RunMeta -Config $config | Out-Null

$results = New-Object "System.Collections.Generic.List[object]"

# --- Define the test order (collect-all) ---
$testSequence = @(
    "test_p0_state_display.ps1",
    "test_p1_worker_kill.ps1",
    "test_p1_core_kill.ps1",
    "test_p1_power_loss.ps1",
    "test_p3_partial_write.ps1",
    "test_p3_watchdog_spam.ps1",
    "test_p2_lock_stress.ps1",
    "test_p2_multi_worker.ps1"  # quarantine
)

# --- Run P0 first; if P0 fails, skip everything else (precondition_failed) ---
Write-Host "=== Running P0: Preconditions ===" -ForegroundColor Yellow
Write-Host ""

$p0Script = Join-Path $PSScriptRoot "test_p0_state_display.ps1"
if (Test-Path $p0Script) {
    $p0Result = & $p0Script
    $results.Add($p0Result) | Out-Null
    $p0Failed = ($p0Result.status -eq "FAIL")
} else {
    Write-Host "[ERROR] P0 script not found: $p0Script" -ForegroundColor Red
    $p0Failed = $true
}

Write-Host ""

if ($p0Failed) {
    Write-Host "=== P0 FAILED: Skipping remaining tests ===" -ForegroundColor Red
    Write-Host ""
}

# --- Run remaining tests ---
foreach ($script in $testSequence[1..($testSequence.Count-1)]) {
    $testName = [System.IO.Path]::GetFileNameWithoutExtension($script)

    if ($p0Failed) {
        $results.Add((Mark-Skipped -TestName $testName -Reason "precondition_failed" -TestsRoot $config.tests_root)) | Out-Null
        continue
    }

    if (Should-SkipQuarantineTest -TestName $testName -Config $config) {
        $results.Add((Mark-Skipped -TestName $testName -Reason "quarantine_skipped_by_default" -TestsRoot $config.tests_root)) | Out-Null
        continue
    }

    $path = Join-Path $PSScriptRoot $script
    
    if (-not (Test-Path $path)) {
        $results.Add((Mark-Skipped -TestName $testName -Reason "script_not_found" -TestsRoot $config.tests_root)) | Out-Null
        continue
    }
    
    try {
        $r = & $path
        # enforce shape
        if (-not $r.test -or -not $r.status) { throw "Test did not return a valid result object." }
        $results.Add($r) | Out-Null
    } catch {
        # If a test script crashes without producing a result, convert to FAIL here
        $dir = New-TestDir -Root $config.tests_root -TestName $testName
        $stdout = Join-Path $dir "stdout.log"
        $_ | Out-String | Out-File -FilePath $stdout -Append -Encoding utf8

        $fail = New-TestResult -Test $testName -Pass $false -Status "FAIL" -DurationMs 0 -Message $_.Exception.Message -Artifacts @($stdout)
        Write-TestReport -Result $fail -TestDir $dir -StdoutLogPath $stdout | Out-Null
        $results.Add($fail) | Out-Null
    }
}

# --- Finalize ---
Write-Host ""
Write-Host "=== Finalizing Report ===" -ForegroundColor Cyan
Write-Host ""

$final = Finalize-Report -Config $config -Results $results
$exit = Get-ExitCode -FinalReport $final -TreatP0FailureAs2:$true

Write-Host "=== Test Suite Summary ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Total: $($final.total_tests)" -ForegroundColor Gray
Write-Host "Passed: $($final.passed)" -ForegroundColor Green
Write-Host "Failed: $($final.failed)" -ForegroundColor $(if ($final.failed -gt 0) { "Red" } else { "Gray" })
Write-Host "Skipped: $($final.skipped)" -ForegroundColor Yellow
Write-Host ""
Write-Host "Report: $($config.final_report_path)" -ForegroundColor Cyan
Write-Host ""

if ($exit -eq 0) {
    Write-Host "STATUS: PASS" -ForegroundColor Green
} elseif ($exit -eq 2) {
    Write-Host "STATUS: FAIL (P0 preconditions not met)" -ForegroundColor Red
} else {
    Write-Host "STATUS: FAIL" -ForegroundColor Red
}

exit $exit
