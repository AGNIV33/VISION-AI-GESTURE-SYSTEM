# PRD: Vision AI Gesture System

**Status:** Draft v0.1 (for owner review)
**Owner:** Agniv Sarkar
**Last updated:** 2026-10-27

---

## 1. One-line summary

A Windows desktop app that uses a normal webcam to track your hands, so you can control your PC with Apple Vision Pro-style gestures: point, tap, drag, scroll, zoom, rotate, and more.

## 2. Problem

- Today you need a mouse, a touchpad, or an expensive headset to use your PC.
- Touch-free control helps with presentations, cooking or messy hands, accessibility, kiosks, and the "wow" factor.
- Existing webcam gesture tools are often shaky, laggy, or support only a few gestures.

## 3. Target users

| User | Why they want it |
|---|---|
| Tech enthusiasts | Want a "Vision Pro on my laptop" experience |
| Presenters and teachers | Control slides and pointer from a distance |
| People who cook, draw, or work with dirty hands | Use the PC without touching it |
| Users with some motor limits | An alternative input method (not a medical device) |
| Content creators and streamers | A cool, visible way to control their screen |

## 4. Goals (v1)

1. **Buttery smooth cursor**: no visible shake when the hand is still, no visible lag when moving.
2. **Reliable gestures**: very few false clicks and few missed gestures.
3. **Works with any normal webcam** on Windows 10 and Windows 11.
4. **Simple setup**: a first-run wizard gets a new user working in under 2 minutes.
5. **Runs quietly in the system tray** until the user quits.
6. **Sellable**: installer, licensing, free plan and paid plan.

## 5. Non-goals (v1)

- Eye tracking ("look to select" like Vision Pro). This is not reliable with a normal webcam.
- macOS or Linux support.
- Depth cameras (Intel RealSense, Leap Motion). Maybe in a later version.
- VR or AR headsets.
- Custom user-made gestures (later version).
- Controlling apps that run as Administrator (Windows blocks this by default; see Risks).

## 6. Gesture list (v1)

Vision Pro uses eyes to aim and fingers to act. Our app uses **hand position to aim** and **fingers to act**.

| # | Gesture | How to do it | PC action | Plan |
|---|---|---|---|---|
| 1 | Point / Move | Open hand facing the camera, then move it | Moves the cursor | Free |
| 2 | Tap | Quick pinch (thumb + index), then release | Left click | Free |
| 3 | Scroll | Raise index + middle fingers together ("two-finger pose"), then move the hand up/down/left/right | Scroll with smooth inertia | Free |
| 4 | Double tap | Two quick pinches | Double click | Paid |
| 5 | Pinch and drag | Pinch, hold, move, release | Click-and-drag (move windows, select text, drag files) | Paid* |
| 6 | Right click | Thumb + middle finger pinch | Right click / context menu | Paid |
| 7 | Two-hand zoom | Pinch with both hands, then move them apart or together | Real pinch-zoom (touch injection); Ctrl+scroll as a backup | Paid |
| 8 | Two-hand rotate | Pinch with both hands, then rotate them like a steering wheel | Real rotate gesture (touch injection) | Paid |
| 9 | Palm "Home" | Show your palm and pinch | Opens Task View (Win+Tab) | Paid |
| 10 | Pause / Resume | Make a fist and hold it for 1.5 s (or use a hotkey or the tray) | Turns gesture control on/off | Free |

\* **Open decision:** the free plan has 2-3 gestures. The suggested free set is **Move + Tap + Scroll** (plus Pause, which is a safety feature). Drag could be free instead of Scroll. The owner decides later.

## 7. Functional requirements

### 7.1 Tracking
- FR-1: Track up to 2 hands with 21 landmarks each (MediaPipe Hand Landmarker).
- FR-2: Know left from right hand. Support left-handed users (choose the main hand in settings).
- FR-3: Mirror the camera image so moving right moves the cursor right.

### 7.2 Cursor
- FR-4: Map an adjustable "active box" in the camera view to the whole screen, including multi-monitor setups.
- FR-5: Two modes: **Absolute** (hand position = screen position, the default) and **Trackpad** (relative movement with acceleration).
- FR-6: Smoothing with the One Euro Filter, a dead zone, and cursor freeze while a pinch starts (so clicking doesn't move the cursor).

### 7.3 Gestures
- FR-7: Every gesture can be turned on/off in Settings.
- FR-8: Every threshold (pinch distance, hold time, and so on) has a good default and can be tuned.
- FR-9: Gestures work at different distances from the camera (all measurements are scaled by hand size).

### 7.4 App shell
- FR-10: First-run setup wizard: camera choice, camera test, main hand, quick gesture tutorial.
- FR-11: Settings window with tabs (see DESIGN.md).
- FR-12: System tray icon with a menu: Pause/Resume, Settings, Show camera preview, Quit.
- FR-13: Closing the Settings window hides it; the app keeps running in the tray. Only "Quit" exits.
- FR-14: Optional "Start with Windows" (on by default, can be turned off).
- FR-15: Optional on-screen feedback overlay (a ring around the cursor that fills when you pinch).
- FR-16: Global hotkey to pause/resume (default: Ctrl+Alt+G).

### 7.5 Licensing (built last)
- FR-17: Free plan unlocks the free gestures; a license key unlocks all.
- FR-18: A developer/owner mode with everything unlocked.
- FR-19: License check works offline for some days after activation.

## 8. Non-functional requirements (targets to measure, not promises)

| Area | Target |
|---|---|
| Tracking speed | 30 fps or more on a normal laptop (e.g., Intel i5 8th gen or newer) |
| Cursor update rate | Cursor redrawn at screen rate (60 Hz+) using prediction between camera frames |
| Delay (hand move → cursor move) | Under ~80 ms |
| CPU use | Under ~15% on a 4-core laptop while tracking |
| RAM | Under ~300 MB |
| False clicks | Fewer than 1 per 10 minutes of normal use |
| Startup | Tray icon visible in under 5 s |
| Privacy | All processing on the device. No video is saved or sent anywhere. |

## 9. Success metrics (after launch)

- 7-day retention of free users
- Free → paid conversion rate
- Average session length with gestures on
- Number of crash reports (should trend to zero)

## 10. Risks

| Risk | Impact | Plan |
|---|---|---|
| Bad lighting makes tracking shaky | Users think the app is broken | Light check in the setup wizard and tips in the app |
| Webcam is only 15 fps in low light | Laggy feel | Show the fps in the preview; prediction between frames |
| Antivirus flags the .exe | Users can't install | Nuitka build + code-signing certificate |
| Windows blocks input into Admin apps (UIPI) | Gestures don't work in some windows | Show a notice; later, an optional signed "uiAccess" build |
| Tired arms ("gorilla arm") | Users stop using it | Small active box, trackpad mode, hand can rest low |
| MediaPipe Python changes or drops support | Build breaks | Pin versions; keep the tracker behind an interface |

## 11. Open questions (owner to decide)

1. Which 2-3 gestures are free? (Suggested: Move, Tap, Scroll.)
2. Price and payment provider (Lemon Squeezy, Gumroad, or other).
3. App name and logo (working name: "Vision AI").
4. Lifetime license or yearly subscription?
