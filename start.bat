@echo off
setlocal
cd /d "%~dp0"

if not exist "venv\Scripts\pythonw.exe" (
  echo [First run] Creating virtual environment and installing dependencies...
  where python >nul 2>nul
  if errorlevel 1 (
    py -3 -m venv venv
  ) else (
    python -m venv venv
  )
  if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Failed to create venv. Install Python 3.9+ and enable "Add Python to PATH".
    pause
    exit /b 1
  )
  "venv\Scripts\python.exe" -m pip install --upgrade pip >nul 2>nul
  "venv\Scripts\python.exe" -m pip install -r requirements.txt
  if not exist "venv\Scripts\pythonw.exe" (
    echo [ERROR] Dependency install failed. Check network, or run manually:
    echo     venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
  )
)

start "" "venv\Scripts\pythonw.exe" "LC2TrainerGUI.py"
exit /b 0