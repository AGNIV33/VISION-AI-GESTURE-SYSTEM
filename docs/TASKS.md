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
- [ ] Trackpad mode with acceleration
- [x] Dead zone
- [~] High-rate cursor thread (~120 Hz) with light prediction (logic tested; feel needs the owner's PC)
- [ ] **Checkpoint:** owner says the cursor feels smooth

## Phase 3: Core gestures
- [~] Gesture state machine (`gestures/recognizer.py`, `hand_pose.py`, `actions/dispatcher.py`)
- [~] Tap (with cursor freeze on pinch start)
- [~] Double tap (second tap snaps to the first tap's spot; Windows turns two clicks into a double-click)
- [~] Right click (thumb + middle)
- [~] Drag (pinch + move, or pinch held 0.4 s)
- [~] Scroll (two-finger pose, vertical + horizontal)
- [ ] Scroll inertia
- [~] Pause / resume (fist held 1.5 s, or P in the preview)
- [ ] Global pause hotkey (with the app shell, Phase 6)
- [x] Tests for each gesture with made-up hand data
- [ ] Tests with recorded real hand data
- [ ] **Checkpoint:** browse a site and move files using gestures only

## Phase 4: Two-hand gestures
- [ ] `win_touch.py`: touch injection (2 contacts)
- [ ] Zoom (with Ctrl+wheel backup)
- [ ] Rotate
- [ ] Priority rules (two-hand beats one-hand)
- [ ] **Checkpoint:** zoom works in Edge/Chrome and Photos

## Phase 5: System gestures
- [ ] Palm-facing detection
- [ ] Home gesture → Win+Tab
- [ ] **Checkpoint:** no false triggers in 10 minutes of normal use

## Phase 6: App shell
- [ ] Single-instance lock
- [ ] Tray icon + menu (Pause, Preview, Settings, Quit)
- [ ] Settings model (pydantic) + JSON save/load + live apply
- [ ] Settings window with all tabs (DESIGN.md 2.2 B)
- [ ] Setup wizard (4 steps)
- [ ] Feedback overlay (click-through ring)
- [ ] Start with Windows (registry Run key)
- [ ] Close-to-tray + one-time balloon tip
- [ ] Dark glass theme (`theme.qss`)
- [ ] **Checkpoint:** a new user can set up in under 2 minutes

## Phase 7: Polish + speed
- [ ] Measure CPU, RAM, delay; meet PRD targets
- [ ] Low-light warning
- [ ] Admin-window (UIPI) notice
- [ ] Error handling: camera unplugged, camera in use by another app
- [ ] Final tuning of default thresholds with the owner

## Phase 8: Packaging
- [ ] `scripts/build.ps1` (Nuitka standalone)
- [ ] `installer/vision_ai.iss` (Inno Setup)
- [~] App icon + version info (icon done: `assets/icons/app.ico`; version info later)
- [ ] Test on a clean Windows PC / VM

## Phase 9: Licensing
- [ ] Choose a provider (Lemon Squeezy / Keygen / other)
- [ ] `licensing/features.py`: free vs paid gesture list
- [ ] License key activation + offline grace period
- [ ] Owner/developer mode (everything unlocked)
- [ ] License tab in Settings

## Phase 10: Launch prep
- [ ] Code-signing certificate
- [ ] Privacy policy (camera use, no data sent)
- [ ] Website / store page + demo video
- [ ] Release v1.0.0
