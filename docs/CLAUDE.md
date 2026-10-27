# CLAUDE.md

Instructions for Claude when working on this repo.

**Follow every rule in [AGENTS.md](AGENTS.md) first.** This file only adds Claude-specific notes.

## About the owner
- Owner: Agniv Sarkar. Wants answers short, point-wise, in very simple language.
- Explain every change in simple words: what changed, why, and how to test it.
- If something is unclear, ask a short, simple question. Never guess facts or make up results.

## How to work
1. Check [TASKS.md](TASKS.md) and pick the next open task in the current phase.
2. Before a big change (new dependency, new folder, changed design), ask the owner first.
3. Write the code + tests, run `pytest` and `ruff`.
4. Tick the task in TASKS.md.
5. Commit and push with a clear message.
6. Tell the owner exactly what to run on Windows to test it, step by step.

## Things to remember
- Claude's workspace is Linux, but the app is **Windows-only**. Camera and Windows input can't be tested here, so the owner tests on Windows. Never say something "works" unless it was tested.
- Keep `gestures/` pure Python so it can be tested in Claude's workspace.
- "Buttery smooth" is the top goal. Never trade smoothness for features without asking.
- Licensing is built last (Phase 9). Until then, all gestures are on.
- The local project folder is `C:\Users\AGNIV\Desktop\VISION AI`; the GitHub repo is `AGNIV33/VISION-AI-GESTURE-SYSTEM`.
