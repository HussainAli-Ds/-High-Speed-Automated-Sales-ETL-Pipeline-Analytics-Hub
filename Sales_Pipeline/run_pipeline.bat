@echo off
setlocal EnableDelayedExpansion
title Sales ETL Pipeline
color 0A

echo.
echo  =====================================================
echo     SALES ETL PIPELINE  ^|  Async Excel -^> PostgreSQL
echo  =====================================================
echo.

REM ── Move to project root ─────────────────────────────────
cd /d "%~dp0"

REM ── Check for .env ────────────────────────────────────────
if not exist ".env" (
    echo  [ERROR] .env file not found!
    echo  Copy .env.example to .env and fill in your settings.
    pause
    exit /b 1
)

REM ── Start PostgreSQL container ────────────────────────────
echo  [1/4] Starting PostgreSQL Docker container...
docker-compose up -d postgres
if %errorlevel% neq 0 (
    echo  [ERROR] Docker failed. Is Docker Desktop running?
    pause
    exit /b 1
)

REM ── Wait for DB to be healthy ─────────────────────────────
echo  [2/4] Waiting for PostgreSQL to be ready...
timeout /t 8 /nobreak >nul

REM ── Activate venv if present ──────────────────────────────
echo  [3/4] Checking Python environment...
if exist "venv\Scripts\activate.bat" (
    echo       Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo       No venv found — using system Python.
)

REM ── Launch pipeline ───────────────────────────────────────
echo  [4/4] Launching ETL Pipeline...
echo.
python Code\main.py

echo.
echo  Pipeline exited.
pause
endlocal