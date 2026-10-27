@echo off
rem Same app, but with a black window that shows errors. Use this if run_app.bat does nothing.
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python -m vision_ai
echo.
echo The app stopped. Log file: %APPDATA%\VisionAI\logs\vision-ai.log
pause
