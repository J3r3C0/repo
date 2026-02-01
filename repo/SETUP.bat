@echo off
setlocal enabledelayedexpansion

echo ============================================
echo Sheratan System Setup & Installation
echo ============================================
echo.

REM 1. Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)

REM 2. Install Python Dependencies
echo [1/4] Installing Python dependencies...
python -m pip install --upgrade pip
if exist "requirements/core.txt" (
    pip install -r requirements/core.txt
)
if exist "requirements/dev.txt" (
    pip install -r requirements/dev.txt
)
if exist "requirements/extras.txt" (
    pip install -r requirements/extras.txt
)
echo [OK] Python dependencies installed.
echo.

REM 3. Check for Node.js / NPM
npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] NPM/Node.js not found. Please install Node.js and add it to PATH.
    pause
    exit /b 1
)

REM 4. Setup External Services (Dashboard & WebRelay)
echo [2/4] Setting up Dashboard...
if exist "external\dashboard" (
    cd external\dashboard
    echo Running npm install in dashboard...
    call npm install
    echo Building dashboard...
    call npm run build
    cd ..\..
) else (
    echo [WARNING] external\dashboard directory not found.
)
echo.

echo [3/4] Setting up WebRelay...
if exist "external\webrelay" (
    cd external\webrelay
    echo Running npm install in webrelay...
    call npm install
    cd ..\..
) else (
    echo [WARNING] external\webrelay directory not found.
)
echo.

REM 5. Environment Configuration
echo [4/4] Configuring environment...
if not exist ".env" (
    if exist ".env.example" (
        echo [INFO] Creating .env from .env.example...
        copy .env.example .env
    ) else (
        echo [WARNING] .env.example not found. Please create .env manually.
    )
) else (
    echo [INFO] .env already exists.
)

REM Ensure directories exist
if not exist "runtime" mkdir "runtime"
if not exist "logs" mkdir "logs"
if not exist "data\webrelay_out" mkdir "data\webrelay_out"
if not exist "data\webrelay_in" mkdir "data\webrelay_in"

echo.
echo ============================================
echo Setup Complete!
echo You can now start the system with:
echo START_COMPLETE_SYSTEM.bat
echo ============================================
pause
