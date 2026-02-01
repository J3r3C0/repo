@echo off
setlocal enabledelayedexpansion

REM ============================================
REM Sheratan Complete System Start
REM ============================================

echo [SHERATAN] Starting Complete System...
echo.

REM 1. Validation Checks
if not exist "external\dashboard\dist" (
    echo [ERROR] Dashboard build not found at external\dashboard\dist.
    echo         Please run SETUP.bat or "npm run build" in external\dashboard first.
    pause
    exit /b 1
)

if not exist "external\dashboard\node_modules" (
    echo [ERROR] Dependencies not installed. Please run SETUP.bat first.
    pause
    exit /b 1
)

REM Ensure directories exist
if not exist "runtime" mkdir "runtime"
if not exist "logs" mkdir "logs"
if not exist "data\webrelay_out" mkdir "data\webrelay_out"
if not exist "data\webrelay_in" mkdir "data\webrelay_in"
if not exist "config" mkdir "config"

REM Load .env variables
if exist ".env" (
    echo [SHERATAN] Loading .env configuration...
    for /f "usebackq tokens=*" %%a in (".env") do (
        set "line=%%a"
        echo %%a | findstr /r "^#" >nul || echo %%a | findstr /r "^$" >nul || set %%a
    )
)

REM Set PYTHONPATH
set PYTHONPATH=%~dp0;%PYTHONPATH%

REM 2. Service Startup Sequence
echo [1/6] Starting Hub API & Orchestrator (port 8001)...
start "Sheratan Hub" cmd /k "set PYTHONPATH=%~dp0&& cd /d %~dp0 && python -u hub\main.py"
timeout /t 5 /nobreak >nul

echo [2/6] Starting Core Perception Kernel (port 8005)...
start "Sheratan Core" cmd /k "set PYTHONPATH=%~dp0&& cd /d %~dp0 && python -u core\main.py"
timeout /t 3 /nobreak >nul

echo [3/6] Starting Broker (port 9000)...
start "Sheratan Broker" cmd /k "set PYTHONPATH=%~dp0&& cd /d %~dp0 && python hub\mesh\offgrid\broker\auction_api.py --port 9000"
timeout /t 3 /nobreak >nul

echo [4/6] Starting Host-A (port 8081)...
start "Sheratan Host-A" cmd /k "set PYTHONPATH=%~dp0&& cd /d %~dp0 && python hub\mesh\offgrid\host\api_real.py --port 8081 --node_id node-A"
timeout /t 2 /nobreak >nul


echo [5/6] Starting Host-B (port 8082)...
start "Sheratan Host-B" cmd /k "set PYTHONPATH=%~dp0&& cd /d %~dp0 && python hub\mesh\offgrid\host\api_real.py --port 8082 --node_id node-B"
timeout /t 2 /nobreak >nul


echo [5/6] Starting WebRelay (port 3000)...
REM Launch Chrome for WebRelay
powershell -ExecutionPolicy Bypass -File scripts\start_chrome.ps1
cd external\webrelay-v2
start "Sheratan WebRelay" cmd /k "set PORT=3000&& set LLM_BACKEND=chatgpt&& npm start"
cd ..\..
timeout /t 3 /nobreak >nul


echo [6/6] Starting Dashboard (port 3001)...
cd external\dashboard
start "Sheratan Dashboard" cmd /k "set PORT=3001&& npm run dev"
cd ..\..

echo.
echo [WARM-UP] Waiting 15 seconds for services to stabilize...
timeout /t 15 /nobreak >nul

echo.
echo ============================================
echo [SHERATAN] Complete System is LIVE!
echo ============================================
echo.
echo Dashboard:  http://localhost:3001
echo Core UI:    http://localhost:8001/ui
echo Broker:     http://localhost:9000/status
echo.
echo Port Overview (Actual Usage):
echo   - 8001: Core API & State Machine
echo   - 3000: WebRelay (LLM Connector)
echo   - 3001: Control Dashboard
echo   - 9000: Mesh Broker
echo   - 8081/8082: Compute Nodes (A/B)
echo   - : Journal Sync API
echo.
echo To stop: run STOP_SHERATAN.bat
echo ============================================
echo.
pause

