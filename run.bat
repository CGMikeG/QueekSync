@echo off
setlocal EnableDelayedExpansion
title QSync

:: ── Detect where the project lives ──────────────────────────────────────────
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

:: Check if the script is being run from a WSL UNC path (\\wsl.localhost\...)
echo %SCRIPT_DIR% | findstr /i "wsl.localhost" >nul 2>&1
if %errorlevel%==0 (
    goto :run_via_wsl
)

:: ── Native Windows path: use (or create) a Windows venv ─────────────────────
set "VENV=%SCRIPT_DIR%\.venv-win"
set "PYTHON=%VENV%\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo [QSync] Creating Windows virtual environment...
    python -m venv "%VENV%"
    if errorlevel 1 (
        echo [QSync] ERROR: Python not found. Please install Python 3.10+ from https://python.org
        pause
        exit /b 1
    )
    echo [QSync] Installing dependencies...
    "%VENV%\Scripts\pip.exe" install --quiet -r "%SCRIPT_DIR%\requirements.txt"
    echo [QSync] Ready.
)

echo [QSync] Starting (Windows native)...
"%PYTHON%" "%SCRIPT_DIR%\main.py"
goto :eof

:: ── WSL path: delegate to WSL ────────────────────────────────────────────────
:run_via_wsl
echo [QSync] Detected WSL project path. Launching via WSL...

:: Convert UNC path  \\wsl.localhost\Ubuntu\home\gg\QSync
:: to WSL path       /home/gg/QSync
for /f "tokens=*" %%P in ('wsl wslpath -u "%SCRIPT_DIR:\=/%"') do set "WSL_DIR=%%P"

wsl bash -c "cd '%WSL_DIR%' && bash run.sh"
if errorlevel 1 (
    echo.
    echo [QSync] ERROR: Could not launch via WSL.
    echo   Make sure WSL 2 with Ubuntu is installed and WSLg (or an X server) is available.
    pause
)
