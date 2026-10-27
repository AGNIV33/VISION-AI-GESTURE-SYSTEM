# Plan: Vision AI Gesture System

**Status:** Draft v0.1 (waiting for owner review)
**Last updated:** 2026-10-27

---

## 1. What we are building

A Windows app that turns a normal webcam into a hand-gesture controller, with Vision Pro-style gestures, a setup wizard, a settings window, and a tray icon. It will be sold with a free plan (2-3 gestures) and a paid plan (all gestures).

Read next: [PRD.md](PRD.md) (what), [architecture.md](architecture.md) (how), [DESIGN.md](DESIGN.md) (feel and look), [TASKS.md](TASKS.md) (step-by-step work).

## 2. How we work

| Who | Does what |
|---|---|
| **Owner (Agniv)** | Decides features, tests on his Windows PC, gives feedback, approves each phase |
| **Claude (AI coder)** | Writes code, docs, and tests; pushes to GitHub; explains changes simply |

- The code is written in Claude's cloud workspace (Linux) and pushed to GitHub, then copied to `C:\Users\AGNIV\Desktop\VISION AI`.
- **Real testing happens on the owner's Windows PC** (camera + Windows input can't be tested in the cloud).
- Pure logic (gesture rules, filters) is tested automatically with recorded hand data.
- Each phase ends with a **demo checkpoint**: the owner runs it and says "OK" or "fix this".

## 3. Phases and milestones

| Phase | Goal | Done when (demo checkpoint) |
|---|---|---|
| **0. Setup** | Project skeleton, Python env, MediaPipe works on the owner's PC | `python -m vision_ai --check` prints camera + MediaPipe OK |
| **1. Tracking** | Camera + hand tracking + preview window | Preview shows hand points at 30 fps or more |
| **2. Smooth cursor** | Move the cursor with the hand | Cursor feels smooth: no shake when still, no lag when moving |
| **3. Core gestures** | Tap, double tap, right click, drag, scroll, pause | Can browse a website and move files with gestures only |
| **4. Two-hand gestures** | Zoom, rotate | Pinch-zoom works in Edge/Chrome and Photos |
| **5. System gestures** | Home (Task View) | Works without false triggers |
| **6. App shell** | Tray, settings, setup wizard, overlay, autostart, hotkey | A new user can set up in under 2 minutes |
| **7. Polish + speed** | Tuning, CPU use, bug fixes, tests | Meets the targets in PRD section 8 |
| **8. Packaging** | Nuitka build + Inno Setup installer | Installs and runs on a clean Windows PC |
| **9. Licensing** | Free/paid plans, license keys, owner mode | Free plan locks paid gestures; a key unlocks them |
| **10. Launch prep** | Code signing, website/store page, privacy policy, demo video | Ready to sell |

Phases 0–3 are the **MVP** (minimum working version). After phase 3 the owner should already be able to use it daily.

## 4. Decisions already made

- Windows 10/11 only, normal webcam only, no eye tracking.
- Python 3.12 + MediaPipe + OpenCV + PySide6 + Win32 SendInput + touch injection.
- Nuitka for the .exe, Inno Setup for the installer.
- Runs in the system tray until "Quit".
- Freemium: 2-3 free gestures, the rest paid. Free for the owner.
- Licensing is built last.

## 5. Decisions still open

| # | Question | Suggested answer | Needed by |
|---|---|---|---|
| 1 | Which gestures are free? | Move + Tap + Scroll (+ Pause) | Phase 9 |
| 2 | Start with Windows by default? | Yes, with an off switch | Phase 6 |
| 3 | Camera preview in Settings? | Yes, with an off switch | Phase 6 |
| 4 | Price, lifetime vs yearly, payment provider | Decide later | Phase 9 |
| 5 | Final app name and logo | "Vision AI" as the working name | Phase 8 |
| 6 | Scroll gesture: two-finger pose or pinch + move? | Two-finger pose | Phase 3 (can change after testing) |

## 6. Biggest risks (short)

1. Shaky tracking in bad light → light check + tips + strong filtering.
2. Antivirus warnings → Nuitka + code signing.
3. Admin windows block input → notice now, signed uiAccess build later.

Full list: PRD section 10.

## 7. What the owner needs on the PC

- Windows 10 or 11 (64-bit), a webcam.
- Python 3.12 (64-bit) from python.org.
- Git.
- Later (Phase 8): Inno Setup. (Phase 10): a code-signing certificate.
