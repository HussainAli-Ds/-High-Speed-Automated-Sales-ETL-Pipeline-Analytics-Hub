@echo off
setlocal EnableDelayedExpansion
title Sales Pipeline + Dashboard
color 0E

echo.
echo  =====================================================
echo     SALES PIPELINE + DASHBOARD  ^|  Full Stack
echo  =====================================================
echo.

cd /d "%~dp0"

if not exist ".env" (
    echo  [ERROR] .env file not found!
    pause
    exit /b 1
)

REM ── Start PostgreSQL ──────────────────────────────────────
echo  [1/4] Starting PostgreSQL Docker container...
docker-compose up -d postgres
if %errorlevel% neq 0 (
    echo  [ERROR] Docker failed. Is Docker Desktop running?
    pause
    exit /b 1
)

echo  [2/4] Waiting for PostgreSQL to be ready...
timeout /t 8 /nobreak >nul

REM ── Activate venv ────────────────────────────────────────
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM ── Launch both in separate windows ──────────────────────
echo  [3/4] Launching ETL Pipeline in new window...
start "Sales ETL Pipeline" cmd /k "cd /d %~dp0 && python Code\main.py"

timeout /t 3 /nobreak >nul

echo  [4/4] Launching Dashboard in new window...
start "Sales Dashboard" cmd /k "cd /d %~dp0 && python Dashboard\app.py"

echo.
echo  ✅ Both services started in separate windows!
echo  Dashboard: http://localhost:5000
echo.
pause
endlocal