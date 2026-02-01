@echo off
REM Sheratan Hub + Node-A - Final Clean Version

echo [SHERATAN] Starting Hub + Node-A
echo.

REM Create directories
if not exist "runtime" mkdir "runtime"
if not exist "logs" mkdir "logs"
if not exist "data\webrelay_out" mkdir "data\webrelay_out"
if not exist "data\webrelay_in" mkdir "data\webrelay_in"
if not exist "data\chrome_profile" mkdir "data\chrome_profile"
if not exist "config" mkdir "config"

set "ROOT_DIR=%~dp0"

REM Find Chrome
set "CHROME_PATH="
for %%p in ("%ProgramFiles%\Google\Chrome\Application\chrome.exe" "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" "%LocalAppData%\Google\Chrome\Application\chrome.exe") do if exist "%%~p" set "CHROME_PATH=%%~p"

if not defined CHROME_PATH (
    echo [WARNING] Chrome not found - WebRelay will not work
    pause
)

REM Start Chrome Debug
if defined CHROME_PATH (
    echo [1/6] Starting Chrome Debug Mode...
    start "Chrome Debug" "%CHROME_PATH%" --remote-debugging-port=9222 --user-data-dir="%ROOT_DIR%data\chrome_profile" --no-first-run --no-default-browser-check https://chatgpt.com https://gemini.google.com
    timeout /t 3 /nobreak >nul
)

REM Start Core
echo [2/6] Starting Core API / Hub...
start "Sheratan Core" /D "%ROOT_DIR%" cmd /k "set "PYTHONPATH=%ROOT_DIR%" && python -u core\main.py"
timeout /t 8 /nobreak >nul

REM Start Broker
echo [3/6] Starting Broker...
start "Sheratan Broker" /D "%ROOT_DIR%" cmd /k "set "PYTHONPATH=%ROOT_DIR%" && python hub\mesh\offgrid\broker\auction_api.py --port 9000"
timeout /t 3 /nobreak >nul

REM Start Node-A
echo [4/6] Starting Node-A Worker...
start "Sheratan Node-A" /D "%ROOT_DIR%" cmd /k "set "PYTHONPATH=%ROOT_DIR%" && python hub\mesh\offgrid\host\api_real.py --port 8081 --node_id node-A"
timeout /t 2 /nobreak >nul

REM Start WebRelay
echo [5/6] Starting WebRelay...
start "Sheratan WebRelay" /D "%ROOT_DIR%external\webrelay" cmd /k "npm start"
timeout /t 5 /nobreak >nul

REM Start Dashboard
echo [6/6] Starting Dashboard...
start "Sheratan Dashboard" /D "%ROOT_DIR%external\dashboard" cmd /k "npm run dev"

echo.
echo ============================================
echo [SHERATAN HUB] System is LIVE
echo ============================================
echo.
echo Services:
echo   1. Chrome Debug port 9222 - GPT + Gemini
echo   2. Core API / Hub port 8001
echo   3. Broker port 9000
echo   4. Node-A Worker port 8081
echo   5. WebRelay port 3000
echo   6. Dashboard port 3001
echo.
echo Dashboard: http://localhost:3001
echo Core UI: http://localhost:8001/ui
echo.
echo To stop: run STOP_SHERATAN.bat
echo.
pause
