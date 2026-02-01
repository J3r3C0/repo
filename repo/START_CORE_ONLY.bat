@echo off
REM ============================================
REM Sheratan Core System Start (Minimal)
REM Starts Core API without Chrome dependency
REM ============================================

echo [SHERATAN] Starting Core System...
echo.

REM Ensure directories exist
if not exist "runtime" mkdir "runtime"
if not exist "logs" mkdir "logs"
if not exist "data\webrelay_out" mkdir "data\webrelay_out"
if not exist "data\webrelay_in" mkdir "data\webrelay_in"
if not exist "config" mkdir "config"

REM Set PYTHONPATH to repo root for imports
set PYTHONPATH=%~dp0;%PYTHONPATH%

REM Start Core API (from repo root, running core/main.py)
echo [1/2] Starting Core API (port 8001)...
start "Sheratan Core" cmd /k "set PYTHONPATH=%~dp0&& cd /d %~dp0 && python -u core\main.py"
timeout /t 8 /nobreak >nul

REM Verify Core is running
echo [2/2] Verifying Core API...
python -c "import requests; r = requests.get('http://127.0.0.1:8001/health', timeout=5); print(f'Core API: {r.json().get(\"overall\", \"unknown\")}')" 2>nul
if errorlevel 1 (
    echo [WARNING] Core API not responding yet. Check logs\core.log
) else (
    echo [SUCCESS] Core API is running!
)

echo.
echo ============================================
echo [SHERATAN] Core System Started
echo ============================================
echo.
echo Services:
echo   - Core API: http://localhost:8001
echo   - Health: http://localhost:8001/health
echo   - Dashboard: http://localhost:8001/ui
echo.
echo To stop: Close the "Sheratan Core" window or run taskkill /F /IM python.exe
echo.
pause
