# Powershell script to start Chrome with Remote Debugging
$chromePaths = @(
    "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "${env:LocalAppData}\Google\Chrome\Application\chrome.exe"
)

$chromePath = $null
foreach ($path in $chromePaths) {
    if (Test-Path $path) {
        $chromePath = $path
        break
    }
}

if (-not $chromePath) {
    Write-Host "[ERROR] Chrome not found. Please install Chrome or update start_chrome.ps1 with the correct path." -ForegroundColor Red
    exit 1
}

$port = 9222
$userDataDir = Join-Path (Get-Location) "data\chrome_profile"
$targetUrl = "https://chatgpt.com"

Write-Host "[CHROME] Checking if Chrome is already running on port $port..." -ForegroundColor Cyan
$connection = Test-NetConnection -ComputerName localhost -Port $port -InformationLevel Quiet

if ($connection) {
    Write-Host "✅ Chrome is already running with remote debugging." -ForegroundColor Green
    # Navigieren wir trotzdem zu ChatGPT, falls das Fenster nicht offen ist
    Start-Process -FilePath $chromePath -ArgumentList $targetUrl
}
else {
    Write-Host "[CHROME] Starting Chrome with remote debugging on port $port..." -ForegroundColor Cyan
    Write-Host "[CHROME] Profile: $userDataDir" -ForegroundColor Gray
    
    # Ensure profile dir exists
    if (-not (Test-Path $userDataDir)) {
        New-Item -ItemType Directory -Force -Path $userDataDir | Out-Null
    }

    # Start Chrome
    # --remote-debugging-port=9222 is required for WebRelay
    # --user-data-dir ensures we use a dedicated profile for Sheratan
    $chromeArgs = @(
        "--remote-debugging-port=$port",
        "--user-data-dir=`"$userDataDir`"",
        "--no-first-run",
        "--no-default-browser-check",
        $targetUrl
    )
    
    Start-Process -FilePath $chromePath -ArgumentList $chromeArgs

    
    Write-Host "[CHROME] Waiting for Chrome to initialize..." -ForegroundColor Gray
    Start-Sleep -Seconds 5
    
    # Verify again
    $connection = Test-NetConnection -ComputerName localhost -Port $port -InformationLevel Quiet
    if ($connection) {
        Write-Host "✅ Chrome started successfully." -ForegroundColor Green
    }
    else {
        Write-Host "❌ Chrome started but port $port is not responding." -ForegroundColor Red
        exit 1
    }
}
