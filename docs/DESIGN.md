# DESIGN: Vision AI Gesture System

**Status:** Draft v0.1
**Last updated:** 2026-10-27

This file covers two kinds of design:
1. **Gesture design**: how each gesture feels and is detected.
2. **UI design**: the screens, tray, and look.

---

## Part 1: Gesture design

### 1.1 Basic ideas

- **Aim with the hand, act with the fingers** (like Vision Pro uses eyes to aim, fingers to act).
- **Every gesture must be easy to do and hard to do by accident.**
- **The user always knows what the app sees** (overlay ring and tray icon state).
- **Hands can rest.** The active box sits in the middle-lower part of the camera view, so arms don't get tired.

### 1.2 Hand landmarks used

MediaPipe gives 21 points per hand. The important ones:

| ID | Point | Used for |
|---|---|---|
| 0 | Wrist | Hand size, palm facing |
| 4 | Thumb tip | Pinch |
| 5 | Index base (MCP) | **Cursor aim point** (stable during pinch) |
| 8 | Index tip | Pinch, pointing |
| 9 | Middle base | Hand size (wrist → 9) |
| 12 | Middle tip | Right-click pinch, scroll pose |
| 16, 20 | Ring and pinky tips | Fist detection |

**Hand size** = distance from 0 to 9. All distances are divided by it.

### 1.3 Gesture specs (starting values, tuned later)

| Gesture | Starts when | Ends when | Notes |
|---|---|---|---|
| **Move** | One hand visible, not pinched | No hand for 300 ms | Cursor follows the filtered index base (ID 5) |
| **Tap** | Pinch (4↔8) < 0.25 for ≥ 2 frames | Pinch > 0.35 within 300 ms and moved < 0.03 | Cursor is frozen from the pinch start until release |
| **Double tap** | Second tap within 400 ms of the first | — | Sends a real double-click |
| **Drag** | Pinch held and hand moved > 0.03, or held > 350 ms | Pinch > 0.35 | Mouse button stays down while dragging |
| **Right click** | Pinch (4↔12) < 0.25, index NOT pinched | Release | Separate from the index pinch |
| **Scroll** | Index and middle fingers up together, others folded ("two-finger pose") | Pose ends | Hand move up/down/left/right = scroll; release with speed = inertia scroll |
| **Zoom** | Both hands pinched | Either hand releases | Distance change between hands = zoom amount |
| **Rotate** | Both hands pinched | Either hand releases | Angle change of the line between hands = rotation |
| **Home** | Palm faces the camera (all fingers up) + pinch | Release | Win+Tab (Task View) |
| **Pause** | Fist held 1.5 s | — | Toggles pause; tray icon and overlay show the state |

> **Scroll note:** Scroll uses the **two-finger pose** (not "pinch + move") so it never clashes with Drag. This can change after testing.

### 1.4 Smoothness rules

1. One Euro Filter on the aim point (`min_cutoff ≈ 1.0`, `beta ≈ 0.05`; 0.007 added up to 78 ms of lag in testing). Live tuning keys 1-4 in the preview.
2. Dead zone: ignore moves smaller than ~2 pixels when the hand is almost still.
3. Freeze the cursor for the first ~120 ms of a pinch (stops "click drift").
4. The cursor thread moves the real cursor at ~120 Hz toward the target, with tiny prediction.
5. Scroll uses small wheel steps plus inertia, never big jumps.
6. If the camera fps drops below 20, show a "low light" tip.

### 1.5 Feedback

| State | Overlay ring (around the cursor) | Tray icon |
|---|---|---|
| Tracking, idle | Thin white ring | Colored |
| Pinch starting | Ring fills up | Colored |
| Clicked | Short pulse | — |
| Dragging | Solid ring | — |
| Scroll mode | Ring with up/down arrows | — |
| No hand seen | Ring fades out | Colored |
| Paused | No ring | Grey icon |

---

## Part 2: UI design

### 2.1 Look and feel

- **Style:** Calm "glass" style like visionOS: dark, semi-transparent panels, soft rounded corners, clear white text.
- **Colors (draft):**
  - Background `#0F1115` (90% opacity)
  - Panel `#1A1D24`
  - Text `#F5F7FA`, muted text `#9AA3B2`
  - Accent `#5B8CFF` (blue), success `#3DDC97`, warning `#FFB547`, error `#FF5C5C`
- **Font:** Segoe UI Variable (Windows 11), Segoe UI as backup.
- **Corners:** 12 px. **Spacing:** 8 px grid.
- **Light theme:** later; v1 is dark only, plus "Follow Windows" later.

### 2.2 Screens

**A. First-run setup wizard** (4 steps, Back / Next buttons)
1. **Welcome**: what the app does + "All video stays on your PC."
2. **Camera**: pick a camera, live preview, light check (good / too dark).
3. **Your hand**: choose the main hand (right/left), set the active box by moving the hand to the corners.
4. **Try it**: short practice for Move, Tap, Scroll, with a check mark after each success. Then "Finish": the app goes to the tray.

**B. Settings window** (sidebar tabs on the left)

| Tab | Contents |
|---|---|
| General | Start with Windows, pause hotkey, show overlay, language (later) |
| Gestures | A list of all gestures with an on/off switch, a small animation, and a 🔒 for paid ones |
| Tuning | Sliders: cursor speed, smoothing, dead zone, pinch sensitivity, tap time; "Reset to defaults" |
| Camera | Camera choice, resolution, live preview with landmarks, fps and delay shown |
| Cursor | Absolute / Trackpad mode, active box size and position, main hand |
| License | Plan (Free / Pro), enter key, buy button (built last) |
| About | Version, privacy note, logs folder, "Check for updates" (later) |

**C. Tray menu** (right-click the tray icon)
```
● Vision AI: Active
─────────────
Pause gestures      Ctrl+Alt+G
Show camera preview
Settings…
─────────────
Quit Vision AI
```
- Left-click the tray icon = open Settings.
- Closing Settings = hide to tray (a one-time balloon says "Still running in the tray").

**D. Camera preview**: a small floating window with the camera image, hand points drawn, and the current gesture name. Can stay "always on top".

**E. Overlay**: a full-screen, transparent, click-through window that only draws the feedback ring near the cursor.

### 2.3 Accessibility

- All settings can be used with the keyboard.
- Text contrast meets WCAG AA.
- Sliders show numbers, not only bars.
- "Large overlay ring" option.
