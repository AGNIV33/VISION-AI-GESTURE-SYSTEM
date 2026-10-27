@echo off
rem Your hand moves the mouse. Stops by itself after 60 seconds, or press Esc or Q in the window.
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python -m vision_ai --cursor
pause
