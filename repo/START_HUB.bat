@echo off
REM ============================================
REM Sheratan - Start Hub (Core + Broker + Dispatcher)
REM ============================================

echo [HUB] Starting Sheratan Hub...

REM CRITICAL: PYTHONPATH must be set to repo root for imports to work
REM Without this, Python can't find 'core' module and will fail with ModuleNotFoundError
set PYTHONPATH=%~dp0

REM 1. Start Core API
echo [HUB] [1/3] Starting Core API (port 8001)...
start "Sheratan Core" cmd /k "set PYTHONPATH=%~dp0&& cd /d %~dp0 && python -u core\main.py"
timeout /t 5 /nobreak >nul

REM 2. Start Broker (Mesh Distributor)
echo [HUB] [2/3] Starting Broker (port 9000)...
start "Sheratan Broker" cmd /k "set PYTHONPATH=%~dp0&& cd /d %~dp0 && python -u mesh\offgrid\broker\broker_real.py"
timeout /t 3 /nobreak >nul

REM 3. Dispatcher is integrated in Core (no separate process)
echo [HUB] [3/3] Dispatcher integrated in Core

echo.
echo [HUB] Hub started successfully
echo [HUB] Core API: http://localhost:8001
echo [HUB] Broker: http://localhost:9000
echo [HUB] Dispatcher: Running in Core
