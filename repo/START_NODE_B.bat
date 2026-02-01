@echo off
REM ============================================
REM Sheratan Node-B (Remote Machine)
REM Standalone worker node that connects to Hub
REM ============================================

echo [SHERATAN NODE-B] Starting Worker Node...
echo.

REM Configuration
set HUB_IP=192.168.1.100
set HUB_PORT=8001
set BROKER_IP=192.168.1.100
set BROKER_PORT=9000
set NODE_PORT=8082
set NODE_ID=node-B

echo Configuration:
echo   Hub: %HUB_IP%:%HUB_PORT%
echo   Broker: %BROKER_IP%:%BROKER_PORT%
echo   This Node: localhost:%NODE_PORT% (ID: %NODE_ID%)
echo.

REM Ensure directories exist
if not exist "runtime" mkdir "runtime"
if not exist "logs" mkdir "logs"
if not exist "config" mkdir "config"

REM Set PYTHONPATH
set PYTHONPATH=%~dp0;%PYTHONPATH%

REM Start Node-B
echo Starting Node-B Worker...
start "Sheratan Node-B" cmd /k "set PYTHONPATH=%~dp0&& cd /d %~dp0 && python mesh\offgrid\host\api_real.py --port %NODE_PORT% --node_id %NODE_ID% --hub_url http://%HUB_IP%:%HUB_PORT% --broker_url http://%BROKER_IP%:%BROKER_PORT%"

echo.
echo ============================================
echo [SHERATAN NODE-B] Worker Node is LIVE!
echo ============================================
echo.
echo This node will:
echo   - Register with Broker at %BROKER_IP%:%BROKER_PORT%
echo   - Accept jobs from Hub at %HUB_IP%:%HUB_PORT%
echo   - Listen on port %NODE_PORT%
echo.
echo To stop: Close the "Sheratan Node-B" window
echo.
pause
