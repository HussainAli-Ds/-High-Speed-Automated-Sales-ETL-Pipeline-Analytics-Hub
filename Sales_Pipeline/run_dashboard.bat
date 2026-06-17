@echo off
setlocal EnableDelayedExpansion
title Sales Dashboard
color 0B

echo.
echo  =====================================================
echo     SALES DASHBOARD  ^|  Taipy Analytics
echo  =====================================================
echo.

cd /d "%~dp0"

if not exist ".env" (
    echo  [ERROR] .env file not found!
    pause
    exit /b 1
)

REM ── Activate venv if present ──────────────────────────────
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

echo  Starting Taipy Dashboard...
echo  Open your browser at: http://localhost:5000
echo.
python Dashboard\app.py

pause
endlocal