#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "==================================================="
echo "  CertApp - Cross-Platform Launcher"
echo "==================================================="

# Detect virtual environment
if [ -d ".venv/Scripts" ]; then
    # Windows Git Bash / MSYS2
    source .venv/Scripts/activate
    echo "[INFO] Running on Windows environment via .venv/Scripts/python"
    python main.py
elif [ -d ".venv/bin" ]; then
    # Linux / macOS
    source .venv/bin/activate
    echo "[INFO] Running on Linux/macOS environment via .venv/bin/python"
    python3 main.py
else
    echo "[ERROR] Virtual environment not found in .venv."
    echo "Please set up .venv first:"
    echo "  Linux/macOS:  python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && pip install -e \".[dev]\""
    echo "  Windows:      python -m venv .venv && source .venv/Scripts/activate && pip install -r requirements.txt && pip install -e \".[dev]\""
    exit 1
fi
