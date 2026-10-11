@echo off
setlocal
cd /d "%~dp0"

echo ===================================================
echo   CertApp - Windows Launcher
echo ===================================================

REM Check if .venv exists
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Virtual environment not found. Setting up .venv...
    where python >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Python was not found in PATH. Please install Python 3.11+ from python.org and check "Add Python to PATH".
        pause
        exit /b 1
    )
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [INFO] Installing project dependencies...
    call .venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    pip install -e ".[dev]"
) else (
    call .venv\Scripts\activate.bat
)

echo [INFO] Starting CertApp...
python main.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] CertApp exited with an error.
    pause
)
