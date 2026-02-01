# Check if Chrome is running with Remote Debugging on port 9222
$port = 9222
$processName = "chrome"

Write-Host "[CHECK] Verifying Chrome Remote Debugging on port $port..." -ForegroundColor Cyan

$connection = Test-NetConnection -ComputerName localhost -Port $port -InformationLevel Quiet

if ($connection) {
    Write-Host "✅ Chrome Remote Debugging is ACTIVE on port $port." -ForegroundColor Green
    exit 0
} else {
    Write-Host "❌ Chrome Remote Debugging NOT FOUND on port $port." -ForegroundColor Red
    Write-Host "Please start Chrome with: --remote-debugging-port=9222" -ForegroundColor Yellow
    
    $chromeProc = Get-Process $processName -ErrorAction SilentlyContinue
    if ($chromeProc) {
        Write-Host "Note: Chrome IS running, but maybe without the debugging flag." -ForegroundColor Gray
    } else {
        Write-Host "Note: Chrome is NOT running." -ForegroundColor Gray
    }
    
    exit 1
}
