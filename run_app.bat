@echo off
rem Starts the Vision AI tray app (no black window). Find it near the clock.
cd /d "%~dp0"
start "" ".venv\Scripts\pythonw.exe" -m vision_ai
