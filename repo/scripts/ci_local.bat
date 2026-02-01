@echo off
setlocal enabledelayedexpansion

REM --- Use python from PATH
python -V
if errorlevel 1 (
  echo [ERR] Python not found in PATH
  exit /b 2
)

REM --- Install dev requirements (idempotent)
pip install -r requirements-dev.txt
if errorlevel 1 (
  echo [ERR] pip install failed
  exit /b 2
)

REM --- Phase-1 gate
python tools\verify_phase1.py
if errorlevel 1 (
  echo [ERR] Phase-1 verify failed
  exit /b 2
)

REM --- Tests
pytest -v
if errorlevel 1 (
  echo [ERR] Tests failed
  exit /b 2
)

echo [OK] CI local passed
exit /b 0
