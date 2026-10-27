@echo off
rem Makes a license key (owner only). First time: tools\make_license.py --init
cd /d "%~dp0"
call .venv\Scripts\activate.bat
set /p WHO=Email or name for the key: 
set /p PLAN=Plan (owner = free for you, pro = for a buyer): 
python tools\make_license.py --who "%WHO%" --plan %PLAN%
pause
