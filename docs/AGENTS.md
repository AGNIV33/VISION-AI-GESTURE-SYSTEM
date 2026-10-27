# AGENTS.md: Rules for AI coding agents

These rules apply to any AI agent (Claude, Copilot, Cursor, Codex, etc.) working on this repo.

## 1. Read first
1. [plan.md](plan.md): phases and how we work
2. [PRD.md](PRD.md): what to build
3. [architecture.md](architecture.md): how it is built (threads, folders, data types)
4. [DESIGN.md](DESIGN.md): gesture specs and UI
5. [TASKS.md](TASKS.md): what to do next

Work only on the **current phase** in TASKS.md unless the owner says otherwise.

## 2. Project facts
- Windows 10/11 desktop app, Python 3.12 (64-bit).
- Main libraries: `mediapipe`, `opencv-contrib-python` (MediaPipe requires it; never also install `opencv-python`), `numpy`. Added later: `PySide6`, `pydantic` (Phase 6).
- Windows APIs via `ctypes` only (no `pyautogui`, no `pywin32` unless agreed).
- Source code lives in `src/vision_ai/`. Tests in `tests/`.

## 3. Commands
```powershell
# Setup (Windows, PowerShell)
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

# Run
python -m vision_ai            # normal app (tray)
python -m vision_ai --check   # camera + MediaPipe check
python -m vision_ai --debug   # with preview + debug info

# Test and lint
pytest
ruff check src tests
ruff format src tests
mypy src
```

## 4. Coding rules
- Type hints everywhere. `from __future__ import annotations` at the top of each module.
- Small modules, one job each (see architecture.md section 4).
- **Windows-only code stays in `actions/` and `platform/`.** Everything in `gestures/` must be pure Python and testable on any OS.
- **Hot loop rules** (capture, tracker, engine, cursor threads):
  - No blocking I/O, no `print`, no sleeping on the UI thread.
  - Reuse numpy arrays; avoid creating many objects per frame.
  - Never touch Qt widgets from a worker thread. Use Qt signals.
- Every magic number (threshold, timing) goes in `config/defaults.py` with a comment, never inline.
- All distances in the gesture code are **scaled by hand size**.
- Log with `logging.getLogger(__name__)`. Never log images.
- Never save or upload camera frames.

## 5. Testing rules
- New gesture logic needs a test that uses recorded landmark data.
- Don't merge if `pytest` or `ruff` fails.
- The Windows input code can't be tested in CI; add a manual test script in `tools/` and list the steps in the PR.

## 6. Git rules
- Branch names: `phase-N/short-name` (e.g. `phase-2/one-euro-filter`).
- Commit messages: Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`).
- Update TASKS.md in the same commit as the work.
- Never commit: `.venv/`, build output, `*.exe`, license secrets, API keys.

## 7. Do not
- Never name a Thread attribute `_stop` (it breaks `Thread.join`); use `_stop_evt`.
- Don't add new big dependencies without asking the owner.
- Don't change gesture defaults without saying why in the commit.
- Don't add telemetry or any network calls (except licensing, Phase 9).
- Don't use third-party MediaPipe model copies; their licenses may forbid commercial use. Use only the official Google model.
