# VISION-AI-GESTURE-SYSTEM

Control your Windows PC with hand gestures using a normal webcam (Vision Pro-style).
Docs are in [`docs/`](docs/): start with [`plan.md`](docs/plan.md).

**Status:** Phases 0-2 written (tracking + smooth cursor). Needs testing on a Windows PC.

## Easiest way (Windows)

Double-click `setup.bat` once, then `run_debug.bat` or `run_cursor.bat`.

## Setup by hand (Windows, PowerShell)

```powershell
cd "$HOME\Desktop\VISION AI"
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope Process Bypass
pip install -e ".[dev]"
python scripts/download_model.py    # one-time download of Google's hand model
```

## Run

```powershell
python -m vision_ai --check     # 1. is my PC ready? (camera, model, speed)
python -m vision_ai --debug     # 2. see hand tracking. Does NOT touch the mouse.
python -m vision_ai --cursor    # 3. hand moves the mouse (auto-stops after 60 s)
```

In the preview window: **Esc / Q** = quit, **P** = pause/resume mouse control.
Useful options: `--camera 1`, `--backend msmf`, `--main-hand left`, `--seconds 0` (never auto-stop).

## Develop

```powershell
pytest
ruff check src tests
ruff format src tests
```
