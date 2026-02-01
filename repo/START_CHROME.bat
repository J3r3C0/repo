@echo off
REM ============================================
REM Sheratan - Start Chrome with Debug Port
REM ============================================

echo [CHROME] Starting Chrome with debug port 9222...

REM Find Chrome
set CHROME_PATH=
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe
) else if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    set CHROME_PATH=C:\Program Files ^(x86^)\Google\Chrome\Application\chrome.exe
)

if "%CHROME_PATH%"=="" (
    echo [ERROR] Chrome not found!
    exit /b 1
)

REM Start Chrome with debug port and profile
REM CRITICAL: Profile path must be ABSOLUTE, not relative
REM Relative paths cause "cannot read/write" errors when Chrome starts from different CWD
REM Debug port 9222 is required for Puppeteer (WebRelay) to connect
start "Chrome Debug" "%CHROME_PATH%" ^
    --remote-debugging-port=9222 ^
    --user-data-dir="%~dp0data\chrome_profile" ^
    --no-first-run ^
    --no-default-browser-check ^
    https://chatgpt.com ^
    https://gemini.google.com

echo [CHROME] Started on port 9222
echo [CHROME] Profile: %~dp0data\chrome_profile
echo [CHROME] Tabs: ChatGPT + Gemini
echo.
echo [INFO] First time? Log in to ChatGPT and Gemini (session will be saved)
