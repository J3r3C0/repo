@echo off
REM ============================================
REM Sheratan - Start WebRelay Worker
REM ============================================

echo [WEBRELAY] Starting WebRelay Worker...

REM 1. Start Chrome first (if not already running)
echo [WEBRELAY] Checking Chrome...
powershell -Command "Test-NetConnection -ComputerName localhost -Port 9222 -InformationLevel Quiet -WarningAction SilentlyContinue" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [WEBRELAY] Chrome not running, starting...
    call "%~dp0START_CHROME.bat"
    echo [WEBRELAY] Waiting 5 seconds for Chrome to initialize...
    timeout /t 5 /nobreak >nul
) else (
    echo [WEBRELAY] Chrome already running on port 9222
)

REM 2. Install dependencies if needed
if not exist "external\webrelay\node_modules" (
    echo [WEBRELAY] Installing dependencies...
    cd external\webrelay
    call npm install
    cd ..\..
)

REM 3. Start WebRelay
echo [WEBRELAY] Starting worker on port 3000...
cd external\webrelay
start "Sheratan WebRelay" cmd /k "npm start"
cd ..\..

echo [WEBRELAY] Worker started
echo [WEBRELAY] Endpoint: http://localhost:3000
