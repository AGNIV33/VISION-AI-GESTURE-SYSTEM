@echo off
rem Shows hand tracking. Does NOT move the mouse. Close with Esc or Q in the window.
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python -m vision_ai --debug
pause
