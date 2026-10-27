# Architecture: Vision AI Gesture System

**Status:** Draft v0.1
**Last updated:** 2026-10-27

---

## 1. Tech stack

| Layer | Choice | Notes |
|---|---|---|
| Language | Python 3.12 (64-bit) | Confirm the MediaPipe wheel for this version in Phase 0 |
| Hand tracking | MediaPipe Tasks: Hand Landmarker (`hand_landmarker.task`) | Apache 2.0, commercial use allowed. Use only the official Google model. |
| Camera | OpenCV (`cv2.VideoCapture`, MSMF/DirectShow backend) | 640x480 is enough for tracking and is fast |
| UI + tray | PySide6 (Qt 6) | `QSystemTrayIcon`, settings window, overlay |
| Mouse / keyboard | Win32 `SendInput` via `ctypes` | Absolute coordinates on the virtual desktop |
| Zoom / rotate | Win32 touch injection (`InitializeTouchInjection`, `InjectTouchInput`) via `ctypes` | Real two-finger gestures; Ctrl+wheel backup |
| Settings storage | JSON file + `pydantic` models | `%APPDATA%\VisionAI\settings.json` |
| Logs | Python `logging` with a rotating file | `%LOCALAPPDATA%\VisionAI\logs\` |
| Tests | `pytest` | The gesture logic is pure Python and testable on any OS |
| Build | Nuitka (`--standalone`) | Faster start; harder to copy than PyInstaller |
| Installer | Inno Setup | Start menu shortcut, uninstaller, optional autostart |
| Licensing (later) | Lemon Squeezy or Keygen API | Hidden behind `licensing/` |

## 2. Big picture

```
 ┌───────────┐   newest frame   ┌────────────┐  landmarks  ┌────────────────┐  events  ┌──────────────────┐
 │  Capture  │ ───────────────▶ │  Tracker   │ ──────────▶ │ Gesture Engine │ ───────▶ │ Action Dispatcher│
 │  thread   │  (queue size 1)  │  thread    │             │ (filters +     │          │ (SendInput,      │
 │  OpenCV   │                  │  MediaPipe │             │  state machines)│          │  touch inject)   │
 └───────────┘                  └────────────┘             └────────────────┘          └──────────────────┘
                                                                   │  cursor target             ▲
                                                                   ▼                            │
                                                          ┌────────────────┐   120 Hz ticks     │
                                                          │ Cursor Smoother│ ───────────────────┘
                                                          │ (prediction)   │
                                                          └────────────────┘
        ┌─────────────────────────────── Qt main thread (UI) ───────────────────────────────┐
        │ Tray icon · Settings window · Setup wizard · Camera preview · Feedback overlay     │
        └─────────────────── talks to the engine only through Qt signals / queues ───────────┘
```

## 3. Threads and why

Smoothness comes from **never letting one slow part block another**.

| Thread | Job | Rule |
|---|---|---|
| **Capture** | Reads frames from the webcam | Keeps only the **newest** frame (queue size 1). Old frames are dropped, so lag never builds up. |
| **Tracker** | Runs MediaPipe on the newest frame | Runs in `VIDEO` mode with a timestamp. Outputs landmarks plus a timestamp. |
| **Engine** | Filters landmarks, finds gestures | Pure Python, no I/O. Turns landmarks into `GestureEvent`s and a cursor target. |
| **Cursor** | Moves the cursor at a high rate (about 120 Hz) | Moves smoothly toward the latest target, with small prediction, so the cursor moves faster than the camera's 30 fps. |
| **Qt main** | All UI | Never runs tracking. Gets updates through Qt signals. |

MediaPipe and OpenCV release Python's GIL during heavy work, so these threads really do run in parallel.

## 4. Folder structure

```
vision-ai-gesture-system/
├── docs/                      # These docs
├── src/vision_ai/
│   ├── __main__.py            # Entry point: python -m vision_ai
│   ├── app.py                 # Builds and wires everything together
│   ├── core/
│   │   ├── capture.py         # CaptureThread
│   │   ├── tracker.py         # TrackerThread + HandFrame data class
│   │   └── pipeline.py        # Starts/stops threads, pause/resume
│   ├── gestures/
│   │   ├── one_euro.py        # One Euro Filter
│   │   ├── features.py        # Pinch distance, finger states, palm facing, scaled by hand size
│   │   ├── recognizer.py      # Runs all gesture state machines
│   │   ├── cursor_mapper.py   # Active box → screen, absolute + trackpad modes
│   │   └── definitions/       # One file per gesture (tap.py, drag.py, scroll.py, zoom.py, ...)
│   ├── actions/
│   │   ├── win_input.py       # SendInput wrappers (move, click, wheel, keys)
│   │   ├── win_touch.py       # Touch injection (zoom, rotate)
│   │   ├── cursor_thread.py   # High-rate smooth cursor mover
│   │   └── dispatcher.py      # GestureEvent → Windows action
│   ├── ui/
│   │   ├── tray.py
│   │   ├── settings_window.py
│   │   ├── setup_wizard.py
│   │   ├── preview.py         # Camera preview with landmarks drawn
│   │   ├── overlay.py         # Click-through feedback ring
│   │   └── theme.qss          # Styles
│   ├── config/
│   │   ├── settings.py        # pydantic Settings model, load/save, migration
│   │   └── defaults.py
│   ├── licensing/
│   │   ├── license.py         # Activate / check key
│   │   └── features.py        # Which gestures each plan unlocks
│   └── platform/
│       ├── dpi.py             # Per-monitor DPI awareness
│       ├── autostart.py       # HKCU\...\Run registry key
│       ├── hotkeys.py         # Global pause hotkey
│       └── single_instance.py # Only one copy of the app may run
├── assets/
│   ├── models/hand_landmarker.task
│   └── icons/
├── tests/                     # pytest, uses recorded landmark files
├── tools/
│   └── record_landmarks.py    # Saves real hand data for tests and tuning
├── scripts/build.ps1          # Nuitka build
├── installer/vision_ai.iss    # Inno Setup script
├── pyproject.toml
└── README.md
```

## 5. Main data types

```python
@dataclass(frozen=True)
class HandFrame:            # Output of the tracker
    t: float                # Time in seconds (monotonic)
    hands: list[Hand]       # 0, 1, or 2 hands

@dataclass(frozen=True)
class Hand:
    side: Literal["left", "right"]
    landmarks: np.ndarray   # shape (21, 3), normalized 0..1 (x, y), z relative
    world: np.ndarray       # shape (21, 3), metres (MediaPipe world landmarks)
    score: float

@dataclass(frozen=True)
class GestureEvent:          # Output of the engine
    kind: GestureKind        # TAP, DOUBLE_TAP, DRAG_START, DRAG_MOVE, DRAG_END, SCROLL, ZOOM, ...
    t: float
    data: dict               # e.g. {"dx": 0, "dy": -120} for SCROLL
```

## 6. Gesture engine design

1. **Scale by hand size.** All distances are divided by the palm length (wrist → middle-finger base). So a pinch looks the same whether the hand is near or far.
2. **Filter first.** Each important landmark passes through a **One Euro Filter**: strong smoothing when slow, little smoothing when fast.
3. **Stable aim point.** The cursor follows a point near the **base of the index finger**, not the fingertip. Fingertips move when you pinch; the base hardly moves. This stops the cursor from jumping during a click.
4. **Hysteresis.** A pinch starts below one threshold (e.g. 0.25) and ends only above a higher one (e.g. 0.35). This stops flicker between "pinched" and "not pinched".
5. **Short confirm time.** A state change needs 2-3 frames in a row to count.
6. **State machines.** Each gesture is a small state machine (`IDLE → PINCH_DOWN → DRAGGING → IDLE`, etc.), so gestures never clash.
7. **Priority rules.** Two-hand gestures beat one-hand gestures. Drag beats tap once the hand moves past a small distance.
8. **Plan gate.** The licensing module says which gestures are on. Locked gestures are ignored.

## 7. Windows input details

- Call `SetProcessDpiAwarenessContext(PER_MONITOR_AWARE_V2)` at startup, so coordinates are right on scaled (125%, 150%) screens.
- Use `SendInput` with `MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK` and coordinates 0..65535 across the virtual desktop. This supports multiple monitors.
- Scrolling uses `MOUSEEVENTF_WHEEL` / `MOUSEEVENTF_HWHEEL` with small steps for smooth scrolling.
- Zoom/rotate use touch injection with 2 contact points. If that fails, fall back to Ctrl + mouse wheel for zoom.
- **Limit:** Windows (UIPI) blocks input into apps running as Administrator unless our app is also elevated or a signed `uiAccess` app. v1 shows a notice; a later version may add a signed uiAccess build.

## 8. Settings

- Saved as JSON in `%APPDATA%\VisionAI\settings.json`, with a `version` field for future changes.
- Changes apply live (the engine gets the new settings through a thread-safe update).
- Includes: camera index, resolution, main hand, active box, cursor mode, smoothing values, per-gesture on/off, thresholds, overlay on/off, autostart, hotkey.

## 9. Privacy and security

- Video frames stay in memory only. They are never written to disk or sent online.
- The only network call is the license check (later).
- Logs never contain images.

## 10. Testing

- Gesture logic is tested with **recorded landmark files** (`tools/record_landmarks.py`), so tests run without a camera and on any OS.
- Windows API wrappers get small manual test scripts.
- A debug panel shows fps, delay, and the current gesture state.

## 11. Build and release

1. `scripts/build.ps1` → Nuitka standalone folder (including the `.task` model and Qt plugins).
2. Inno Setup turns it into `VisionAI-Setup-x.y.z.exe`.
3. Sign the .exe and the installer with a code-signing certificate (before the public sale).
4. Later: an auto-update check.

## 12. Key decisions (ADR-lite)

| Decision | Why | Other options |
|---|---|---|
| Python + MediaPipe | Fastest to build; good tracking | C# + ONNX (slower to build), C++ (much harder) |
| PySide6 | Native tray, modern UI, LGPL (allowed for commercial use when linked dynamically, which is Nuitka's default) | Tkinter (looks old), Electron (heavy) |
| Separate high-rate cursor thread | Makes 30 fps tracking feel like 60-120 fps | Move the cursor only on each frame (looks steppy) |
| Nuitka over PyInstaller | Faster, fewer antivirus issues, harder to copy | PyInstaller (simpler) |
