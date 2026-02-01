@echo off
REM ============================================
REM Sheratan - Start Dashboard
REM ============================================

echo [DASHBOARD] Starting Dashboard...

REM Install dependencies if needed
if not exist "external\dashboard\node_modules" (
    echo [DASHBOARD] Installing dependencies...
    cd external\dashboard
    call npm install
    cd ..\..
)

REM Start Dashboard
echo [DASHBOARD] Starting on port 3001...
cd external\dashboard
start "Sheratan Dashboard" cmd /k "npm run dev"
cd ..\..

echo [DASHBOARD] Dashboard started
echo [DASHBOARD] URL: http://localhost:3001
