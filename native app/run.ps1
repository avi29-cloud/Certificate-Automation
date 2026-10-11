# PowerShell launcher for CertApp
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  CertApp - PowerShell Launcher" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "[INFO] Virtual environment not found. Setting up .venv..." -ForegroundColor Yellow
    python -m venv .venv
    & .venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    pip install -e ".[dev]"
} else {
    & .venv\Scripts\Activate.ps1
}

Write-Host "[INFO] Launching CertApp..." -ForegroundColor Green
python main.py
