@echo off
REM ============================================
REM Sheratan CLI - Simple Commands
REM Usage: sheratan [command] [args]
REM ============================================

setlocal enabledelayedexpansion

if "%1"=="" goto :help

REM Commands
if /i "%1"=="start" goto :start
if /i "%1"=="stop" goto :stop
if /i "%1"=="health" goto :health
if /i "%1"=="status" goto :status
if /i "%1"=="logs" goto :logs
goto :help

:start
    if "%2"=="" (
        echo [ERROR] Usage: sheratan start [chrome^|webrelay^|hub^|dashboard^|all]
        exit /b 1
    )
    
    if /i "%2"=="chrome" call "%~dp0START_CHROME.bat"
    if /i "%2"=="webrelay" call "%~dp0START_WEBRELAY.bat"
    if /i "%2"=="hub" call "%~dp0START_HUB.bat"
    if /i "%2"=="dashboard" call "%~dp0START_DASHBOARD.bat"
    if /i "%2"=="all" (
        call "%~dp0START_CHROME.bat"
        timeout /t 5 /nobreak >nul
        call "%~dp0START_HUB.bat"
        timeout /t 5 /nobreak >nul
        call "%~dp0START_WEBRELAY.bat"
        call "%~dp0START_DASHBOARD.bat"
    )
    goto :eof

:stop
    if "%2"=="" (
        echo [STOP] Stopping all Sheratan services...
        taskkill /FI "WINDOWTITLE eq Sheratan*" /F >nul 2>&1
        taskkill /FI "WINDOWTITLE eq Chrome Debug" /F >nul 2>&1
        echo [STOP] All services stopped
    ) else (
        if /i "%2"=="chrome" (
            echo [STOP] Stopping Chrome...
            taskkill /FI "WINDOWTITLE eq Chrome Debug" /F >nul 2>&1
        )
        if /i "%2"=="core" (
            echo [STOP] Stopping Core...
            taskkill /FI "WINDOWTITLE eq Sheratan Core" /F >nul 2>&1
        )
        if /i "%2"=="broker" (
            echo [STOP] Stopping Broker...
            taskkill /FI "WINDOWTITLE eq Sheratan Broker" /F >nul 2>&1
        )
        if /i "%2"=="webrelay" (
            echo [STOP] Stopping WebRelay...
            taskkill /FI "WINDOWTITLE eq Sheratan WebRelay" /F >nul 2>&1
        )
        if /i "%2"=="dashboard" (
            echo [STOP] Stopping Dashboard...
            taskkill /FI "WINDOWTITLE eq Sheratan Dashboard" /F >nul 2>&1
        )
        echo [STOP] Service stopped: %2
    )
    goto :eof

:health
    echo.
    echo ============================================
    echo SHERATAN HEALTH CHECK
    echo ============================================
    echo.
    
    powershell -Command "$ports = @{Chrome=9222;Core=8001;Broker=9000;WebRelay=3000;Dashboard=3001}; $ports.GetEnumerator() | ForEach-Object { $result = Test-NetConnection -ComputerName localhost -Port $_.Value -InformationLevel Quiet -WarningAction SilentlyContinue; Write-Host ('{0,-12} (:{1}): {2}' -f $_.Key, $_.Value, $(if($result){'✓ UP'}else{'✗ DOWN'})) }"
    
    echo.
    echo ============================================
    goto :eof

:status
    echo [STATUS] Fetching system status...
    curl -s http://localhost:8001/api/status 2>nul | python -m json.tool
    goto :eof

:logs
    if "%2"=="" (
        echo [LOGS] Available logs:
        dir /b logs\*.log logs\*.jsonl 2>nul
        echo.
        echo Usage: sheratan logs [filename]
        goto :eof
    )
    
    if exist "logs\%2" (
        type "logs\%2"
    ) else (
        echo [ERROR] Log file not found: logs\%2
    )
    goto :eof

:help
    echo.
    echo Sheratan CLI - Simple Service Management
    echo.
    echo Usage: sheratan [command] [args]
    echo.
    echo Commands:
    echo   start [service]    Start a service (chrome^|webrelay^|hub^|dashboard^|all)
    echo   stop [service]     Stop service(s) (chrome^|core^|broker^|webrelay^|dashboard^|all)
    echo   health             Check service health
    echo   status             Get system status
    echo   logs [file]        View logs
    echo.
    echo Examples:
    echo   sheratan start chrome
    echo   sheratan start all
    echo   sheratan stop webrelay
    echo   sheratan stop
    echo   sheratan health
    echo   sheratan logs core.log
    echo.
    goto :eof
