# 🪟 Windows Setup & Troubleshooting Guide for CertApp

This guide explains how to install, run, test, and troubleshoot **CertApp** on Windows across all common shells (**Git Bash**, **PowerShell**, and **Command Prompt**).

---

## ⚡ Quick Start (Easiest Way)

Just double-click **`run.bat`** in the project folder (or execute `./run.bat` in your terminal).

It will automatically:
1. Detect or create `.venv`
2. Install all required dependencies (including PySide6, PyMuPDF, Pillow, and pytest)
3. Launch CertApp

---

## 💻 Manual Setup by Terminal

Ensure you have **Python 3.11 or newer** installed from [python.org](https://www.python.org/downloads/). During installation, make sure to check **"Add python.exe to PATH"**.

---

### Option 1: Git Bash (MINGW64)

> ⚠️ **CRITICAL FOR GIT BASH USERS:**
> On Windows, the virtual environment executable is **`python`**, NOT `python3`!
> If you type `python3`, Git Bash bypasses the virtual environment and runs the minimal MSYS2 Python or Windows Store alias, causing `ModuleNotFoundError: No module named 'PySide6'`.
> Always use **`python`** inside your venv on Windows!

```bash
# 1. Navigate to the project directory
cd "/c/Users/YourUser/Desktop/certs/Certificate-Automation/native app"

# 2. Create the virtual environment
python -m venv .venv

# 3. Activate the virtual environment
# NOTE: Use forward slashes in Git Bash (not backslashes!)
source .venv/Scripts/activate

# 4. Install all dependencies (including dev/test tools)
pip install -r requirements.txt
pip install -e ".[dev]"

# 5. Run the application (use 'python', NOT 'python3')
python main.py

# 6. Run the test suite
python -m pytest
```

---

### Option 2: Windows PowerShell

```powershell
# 1. (One-time only) Allow script execution if disabled:
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

# 2. Navigate to the project directory
cd "C:\Users\YourUser\Desktop\certs\Certificate-Automation\native app"

# 3. Create virtual environment
python -m venv .venv

# 4. Activate virtual environment
.venv\Scripts\Activate.ps1

# 5. Install dependencies
pip install -r requirements.txt
pip install -e ".[dev]"

# 6. Run the application
python main.py

# 7. Run the test suite
pytest
```

---

### Option 3: Command Prompt (cmd.exe)

```cmd
:: 1. Navigate to project directory
cd "C:\Users\YourUser\Desktop\certs\Certificate-Automation\native app"

:: 2. Create virtual environment
python -m venv .venv

:: 3. Activate virtual environment
.venv\Scripts\activate.bat

:: 4. Install dependencies
pip install -r requirements.txt
pip install -e ".[dev]"

:: 5. Run the application
python main.py

:: 6. Run the test suite
pytest
```

---

## 🔍 Why Did Errors Happen? (Detailed Explanations)

### 1. `ModuleNotFoundError: No module named 'PySide6'` with `python3 main.py`
* **Why it happened:**
  Windows CPython only installs `python.exe` inside `.venv\Scripts\`. It does **not** create a `python3.exe`.
  When you type `python3` in Git Bash, bash looks for `python3.exe` inside `.venv\Scripts\`, doesn't find it, and falls back to:
  - `/usr/bin/python3` (MSYS2's internal Cygwin-like python), or
  - `WindowsApps\python3.exe` (Microsoft Store stub).
  Neither of those has your virtual environment packages installed!
* **The fix:**
  Always run `python main.py` (not `python3`) on Windows.

---

### 2. `bash: .venvScriptsactivate.bat: command not found`
* **Why it happened:**
  In Git Bash, the backslash `\` is an escape character. Typing `.venv\Scripts\activate.bat` stripped the slashes into `.venvScriptsactivate.bat`.
* **The fix:**
  In Git Bash, use POSIX forward slashes:
  ```bash
  source .venv/Scripts/activate
  ```
  (`.bat` is only for CMD, `.ps1` is for PowerShell).

---

### 3. `pytest: command not found`
* **Why it happened:**
  Running `pip install -e .` only installed the runtime dependencies declared in `pyproject.toml`. The testing tools (`pytest` and `pytest-qt`) were only in `requirements.txt`.
* **The fix:**
  `pyproject.toml` has been updated with `[project.optional-dependencies] dev = ["pytest", "pytest-qt"]`.
  Install them with either:
  ```bash
  pip install -r requirements.txt
  # OR
  pip install -e ".[dev]"
  ```
  And run tests reliably using:
  ```bash
  python -m pytest
  ```

---

### 4. `python` opens the Microsoft Store
* **Why it happens:**
  Windows includes execution aliases that intercept `python` and open the Windows Store if Python is not configured in PATH.
* **The fix:**
  1. Open Windows Start menu → Search for **"Manage app execution aliases"**.
  2. Turn **OFF** both toggles for `python.exe` and `python3.exe`.
  3. Ensure your Python path (`C:\Users\<User>\AppData\Local\Programs\Python\Python31x`) is at the top of your User Environment `PATH`.

---

### 5. Moving or Renaming Folders broke `.venv`
* **Why it happens:**
  Python virtual environments contain hardcoded absolute paths in `activate` scripts and `pyvenv.cfg`. If you rename `certs` to `Certs` or move the folder, the venv will point to nonexistent paths and fail with `bad interpreter` or missing modules.
* **The fix:**
  Simply delete `.venv` and recreate it:
  ```bash
  rm -rf .venv          # Git Bash / Linux
  python -m venv .venv
  ```

---

## 🔐 Credentials & Keyring on Windows

CertApp securely stores SMTP passwords using your operating system's credential store:
- On Windows, CertApp automatically uses the **Windows Credential Manager** (`wincred`) via Python's `keyring` package.
- No extra setup is required! Your SMTP passwords remain encrypted and secure.
