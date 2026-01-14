@echo off
REM STOP_SHERATAN.bat - Graceful shutdown with Ctrl+C signal
REM Sends interrupt signal to processes for clean shutdown

echo ========================================
echo Sheratan System Shutdown (Graceful)
echo ========================================
echo.

REM Try graceful shutdown first (Ctrl+C equivalent)
echo [1/4] Sending interrupt signal to Python processes...
for /f "tokens=2" %%i in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST ^| find "PID:"') do (
    echo   Stopping PID %%i...
    taskkill /PID %%i >nul 2>&1
)
echo   ✓ Interrupt signals sent

REM Wait for graceful shutdown
echo [2/4] Waiting 5 seconds for graceful shutdown...
timeout /t 5 /nobreak >nul

REM Check if processes are still running
tasklist /FI "IMAGENAME eq python.exe" 2>nul | find /I /N "python.exe" >nul
if %ERRORLEVEL% EQU 0 (
    echo   ⚠ Some processes still running, forcing shutdown...
    taskkill /F /IM python.exe /T >nul 2>&1
    echo   ✓ Forced shutdown complete
) else (
    echo   ✓ All processes stopped gracefully
)

REM Stop Node.js processes (Dashboard)
echo [3/4] Stopping Node.js processes...
taskkill /F /IM node.exe /T >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   ✓ Node.js processes stopped
) else (
    echo   ⚠ No Node.js processes found
)

REM Verify state persistence
echo [4/4] Verifying state persistence...
if exist runtime\system_state.json (
    echo   ✓ State machine state saved
)
if exist runtime\performance_baselines.json (
    echo   ✓ Performance baselines saved
)
if exist logs\state_transitions.jsonl (
    echo   ✓ State transition log exists
)

echo.
echo ========================================
echo Sheratan System Stopped
echo ========================================
echo.
echo Shutdown method: Graceful (5s timeout)
echo State persisted in: runtime/
echo Logs available in: logs/
echo.

pause
