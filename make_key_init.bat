@echo off
rem ONE TIME: creates your private signing key and the matching public key.
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python tools\make_license.py --init
pause
