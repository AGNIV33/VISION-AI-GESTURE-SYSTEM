# TASKS: Vision AI Gesture System

**How to use:** `[ ]` = to do, `[~]` = written but NOT yet tested on the owner's Windows PC, `[x]` = done and tested.
Update this file in the same commit as the work. Each phase ends with a demo checkpoint for the owner.

---

## Phase 0: Setup
- [x] Write docs (plan, PRD, architecture, DESIGN, AGENTS, CLAUDE, TASKS)
- [x] Owner reviews docs (approved; open questions still listed in plan.md section 5)
- [x] Create `pyproject.toml` (Python 3.10+, version ranges; pin exact versions before release)
- [x] Create the folder structure from architecture.md
- [x] Add `.gitignore`, `README.md` with setup steps
- [x] Download `hand_landmarker.task` into `assets/models/` (script `scripts/download_model.py`)
- [x] Add `python -m vision_ai --check` (camera + MediaPipe check)
- [x] Add a logging setup (basic; file logging comes with the app shell)
- [x] **Checkpoint:** owner runs `--check` on Windows → all OK

## Phase 1: Tracking
- [~] `CaptureThread` with newest-frame slot, 640x480
- [x] `TrackerThread` with MediaPipe Hand Landmarker (VIDEO mode; 1 hand by default, 30 fps on owner's PC)
- [x] Fix swapped left/right labels (owner's test)
- [x] `HandFrame` / `Hand` data classes
- [x] Debug preview window: hand points, fps, delay, speed summary
- [ ] `tools/record_landmarks.py` to save hand data for tests
- [x] **Checkpoint:** preview at 30 fps or more on the owner's PC (30.1 fps, 14-18 ms delay)

## Phase 2: Smooth cursor
- [~] DPI awareness (per-monitor v2)
- [~] `win_input.py`: absolute move on the virtual desktop (also click and wheel helpers, unused until Phase 3)
- [x] One Euro Filter + unit tests (default values are untuned)
- [x] Hand-size scaling in `features.py`
- [x] `cursor_mapper.py`: active box → screen (absolute mode)
- [~] Trackpad mode with acceleration (Settings > Cursor)
- [x] Dead zone
- [~] Aim at the middle of 4 knuckles (steadier) + shorter glide (tau 0.012). Needs owner's feel test
- [~] High-rate cursor thread (~120 Hz) with light prediction (logic tested; feel needs the owner's PC)
- [ ] **Checkpoint:** owner says the cursor feels smooth

## Phase 3: Core gestures
- [~] Gesture state machine (`gestures/recognizer.py`, `hand_pose.py`, `actions/dispatcher.py`)
- [~] Tap (with cursor freeze on pinch start). First real test: did not click -> added `--calibrate`
- [~] Double tap (second tap snaps to the first tap's spot; Windows turns two clicks into a double-click)
- [~] Right click (thumb + middle)
- [~] Drag (pinch + move, or pinch held 0.4 s)
- [~] Scroll (two-finger pose, vertical + horizontal)
- [~] One-hand zoom (thumb on index + middle fingertips, hand up/down = Ctrl+wheel). Quick tap there still clicks
- [~] Scroll inertia (coasts after a fast scroll)
- [~] Pause / resume (fist held 1.5 s, or P in the preview)
- [~] Global pause hotkey (Ctrl+Alt+P, in the app)
- [x] Tests for each gesture with made-up hand data
- [ ] Tests with recorded real hand data
- [ ] **Checkpoint:** browse a site and move files using gestures only

## Phase 4: Two-hand gestures
- [ ] `win_touch.py`: touch injection (2 contacts). NOT built: needs a Windows test machine; Ctrl+wheel used instead
- [~] Two-hand zoom with Ctrl+wheel (pinch with both hands, move apart / closer; Settings: track two hands)
- [ ] Rotate (needs touch injection)
- [~] Priority rules (two-hand beats one-hand)
- [ ] **Checkpoint:** zoom works in Edge/Chrome and Photos

## Phase 5: System gestures
- [x] Palm-facing detection: dropped (palm always faces the camera). Replaced by a ring-finger pinch
- [~] Task View gesture: thumb + ring fingertip held 0.5 s → Win+Tab
- [ ] **Checkpoint:** no false triggers in 10 minutes of normal use

## Phase 6: App shell
- [~] Single-instance lock
- [~] Tray icon + menu (Pause, Settings, Camera, Calibrate, Setup guide, Start with Windows, Quit)
- [~] Settings model (plain dataclass, no pydantic) + JSON save/load + live apply
- [~] Settings window (General, Gestures, Cursor, License, About)
- [~] Setup wizard (welcome, camera, calibrate, finish)
- [~] Feedback overlay (click-through ring)
- [~] Start with Windows (registry Run key)
- [~] Close-to-tray + one-time balloon tip
- [~] Dark theme (`app/theme.py`)
- [ ] **Checkpoint:** a new user can set up in under 2 minutes

## Phase 7: Polish + speed
- [ ] Measure CPU, RAM, delay; meet PRD targets
- [~] Low-light warning
- [~] Admin-window (UIPI) notice
- [~] Error handling: camera unplugged / in use (message + retry every 5 s)
- [ ] Final tuning of default thresholds with the owner

## Phase 8: Packaging
- [~] `scripts/build.ps1` (Nuitka standalone). Written, never run: first build will need fixes
- [~] `installer/vision_ai.iss` (Inno Setup). Written, never run
- [~] App icon + version info (icon + Nuitka version flags)
- [ ] Test on a clean Windows PC / VM

## Phase 9: Licensing
- [ ] Choose a provider (Lemon Squeezy / Keygen / other). Open: keys are made offline with `tools/make_license.py`
- [~] `licensing/features.py`: free vs paid gesture list (free: move, tap, scroll, pause)
- [~] License key activation (offline signed keys; works without internet; optional expiry date)
- [~] Owner mode: an `owner` key made with `tools/make_license.py` unlocks everything
- [~] License tab in Settings

## Phase 10: Launch prep
- [ ] Code-signing certificate (steps in `docs/RELEASE.md`; must be bought)
- [~] Privacy policy draft (`docs/PRIVACY.md`, needs a lawyer's look)
- [~] Website page draft (`website/index.html`); demo video not made
- [ ] Release v1.0.0
