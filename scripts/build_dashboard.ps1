# scripts/build_dashboard.ps1
# Builds the React dashboard for deployment

$REPO_ROOT = $PSScriptRoot + "\.."
$DASHBOARD_DIR = "$REPO_ROOT\external\dashboard"

Write-Host "--- Building Sheratan Dashboard ---" -ForegroundColor Cyan

if (Test-Path "$DASHBOARD_DIR\node_modules") {
    Write-Host "Found node_modules, proceeding to build..."
}
else {
    Write-Host "node_modules not found, running npm install..." -ForegroundColor Yellow
    Push-Location $DASHBOARD_DIR
    npm install
    Pop-Location
}

Push-Location $DASHBOARD_DIR
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "Build FAILED" -ForegroundColor Red
    Pop-Location
    exit 1
}

Write-Host "Build SUCCESSFUL. Output in: $DASHBOARD_DIR\dist" -ForegroundColor Green
Pop-Location
