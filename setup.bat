@echo off
rem First-time setup: makes the environment, installs libraries, downloads the model, runs the check.
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python is not installed.
  echo Install Python 3.12 64-bit from python.org and tick "Add python.exe to PATH", then run this file again.
  pause
  exit /b 1
)
if not exist .venv\Scripts\python.exe (
  py -3.12 -m venv .venv
  if errorlevel 1 (
    echo Python 3.12 not found, trying your default Python instead...
    py -3 -m venv .venv
  )
)
if not exist .venv\Scripts\python.exe (
  echo Could not create the environment. Please send me this screen.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python --version
python -m pip install --upgrade pip
pip install -e ".[dev]"
if errorlevel 1 (
  echo Install failed. Please send me this screen.
  pause
  exit /b 1
)
python scripts\download_model.py
if errorlevel 1 (
  echo Model download failed. Check your internet, then run this file again.
  pause
  exit /b 1
)
echo.
echo ===== Running the PC check =====
python -m vision_ai --check
echo.
pause
