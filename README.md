# VISION-AI-GESTURE-SYSTEM

Control your Windows PC with hand gestures using a normal webcam (Vision Pro-style).
Docs are in [`docs/`](docs/): start with [`plan.md`](docs/plan.md).

**Status (2026-10-27):** all planned parts are written (tracking, cursor, gestures, tray app,
settings, setup guide, licensing, installer scripts). Written on Linux: it needs testing on a
Windows PC. See [`docs/TASKS.md`](docs/TASKS.md) for what is tested (`[x]`) and what is not (`[~]`).

## Easiest way (Windows)

1. Double-click `setup.bat` (first time, and again after updates).
2. Double-click `run_app.bat`. The app opens a setup guide, then lives in the tray (near the clock).
   If nothing appears, use `run_app_debug.bat` to see the error.
3. Right-click the tray icon for Pause / Settings / Quit.

Free for you: double-click `make_key_init.bat` once, then `make_key.bat` (plan `owner`),
and paste the key in Settings > License. See [`docs/RELEASE.md`](docs/RELEASE.md).

## Gestures

| Gesture | How | Plan |
|---|---|---|
| Move | open hand, move it | free |
| Tap / double tap | touch thumb + index fingertip | free |
| Scroll | peace sign, move hand up/down (coasts after a fast flick) | free |
| Pause / resume | fist for 1.5 s, or Ctrl+Alt+P | free |
| Right click | thumb + middle fingertip | pro |
| Drag | pinch, hold, move | pro |
| Zoom (one hand) | thumb on index + middle fingertips, hand up/down | pro |
| Task View | thumb + ring fingertip, hold 0.5 s | pro |
| Zoom (two hands) | pinch with both hands, move apart/closer (turn on "track two hands") | pro |

## Developer tools (OpenCV window, no tray)

```powershell
python -m vision_ai --check       # is my PC ready? (camera, model, speed)
python -m vision_ai --debug       # see hand tracking. Does NOT touch the mouse.
python -m vision_ai --cursor      # hand moves the mouse (auto-stops after 60 s)
python -m vision_ai --calibrate   # measure your pinch numbers
```
Options: `--camera 1`, `--backend msmf`, `--main-hand left`, `--hands 2`, `--seconds 0`.

## Setup by hand (Windows, PowerShell)

```powershell
cd "$HOME\Desktop\VISION AI"
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope Process Bypass
pip install -e ".[dev]"
python scripts/download_model.py    # one-time download of Google's hand model
python -m vision_ai                 # the tray app
```

## Develop

```powershell
pytest
ruff check src tests
ruff format src tests
```

## Build the installer

`.\scripts\build.ps1` (needs Inno Setup 6). Details: [`docs/RELEASE.md`](docs/RELEASE.md).

(c) 2026 Agniv Sarkar. Designed and built by Agniv Sarkar.
