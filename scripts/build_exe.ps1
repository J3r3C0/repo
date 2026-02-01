# scripts/build_exe.ps1
# Builds the Sheratan Core as a standalone EXE using PyInstaller

$REPO_ROOT = $PSScriptRoot + "\.."
Push-Location $REPO_ROOT

Write-Host "--- Bundling Sheratan Core (D1) ---" -ForegroundColor Cyan

# Check for PyInstaller
if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host "PyInstaller not found. Installing..." -ForegroundColor Yellow
    pip install pyinstaller
}

# Run build
pyinstaller --clean sheratan_core.spec

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build FAILED" -ForegroundColor Red
    Pop-Location
    exit 1
}

Write-Host "`nBuild SUCCESSFUL. Executable in: $REPO_ROOT\dist\sheratan_core.exe" -ForegroundColor Green
Pop-Location
