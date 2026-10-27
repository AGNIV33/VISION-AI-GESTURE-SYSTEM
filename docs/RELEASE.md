# RELEASE.md: how to ship Vision AI

Simple steps, in order. Nothing here has been run yet (the build was written on Linux).

## 1. Your license key (free for you)
1. Double-click `make_key_init.bat` **once**. It makes your private key in `%APPDATA%\VisionAI\owner_private.key` and puts the public key into the app. **Back up the private key file.** If you lose it you cannot make new keys; if someone gets it they can make free keys.
2. Double-click `make_key.bat`, type your email, type `owner`. Copy the key it prints.
3. Open the app > Settings > License > paste > Activate. Everything is unlocked.
4. For a buyer: same, but type `pro` (optionally add an expiry with the command line: `--expires 2027-12-31`).

The public key is saved in `src/vision_ai/licensing/public_key.py`. Commit that file (it is safe to share) so every build can check keys.

## 2. Build the installer
1. Install Inno Setup 6 from jrsoftware.org (free).
2. In PowerShell, in the project folder: `.\scripts\build.ps1`
3. Output: `build\launcher.dist\Vision AI.exe` and `dist\VisionAI-Setup-<version>.exe`.
4. Test on a clean PC (or a fresh Windows user): install, first-run guide, tray icon, camera, quit, uninstall.

If the build stops with red text, send it to Claude. MediaPipe is the most likely cause (it has native files that need to be included).

## 3. Digital signature (two kinds)
- **Visible signature (done):** the app says "Designed and built by Agniv Sarkar" and the copyright in Settings > About, and the .exe has the author and copyright in its file properties.
- **Code-signing certificate (you must buy it):** without it, Windows SmartScreen shows "unknown publisher" warnings and some antivirus tools complain. Options: an OV or EV code-signing certificate from a certificate authority (about 100-400 USD a year; EV removes the SmartScreen warning fastest), or Azure Trusted Signing (cheaper, limited countries). After you have it, sign both `Vision AI.exe` and the installer with `signtool sign /fd SHA256 /tr <timestamp-url> /td SHA256 /a <file>`.

## 4. Sell it
- A store that sells software and handles tax for you (Lemon Squeezy, Paddle, Gumroad) is the easiest. They take a cut. After a sale, run `make_key.bat` and email the key (later this can be automated with the store's webhook).
- Put the installer on a download page (`website/index.html` is a draft) and link the privacy policy (`docs/PRIVACY.md`).
- Have a lawyer read the privacy policy and write a short license agreement (EULA) before you charge money.

## 5. Before every release
- [ ] `pytest` and `ruff check` pass
- [ ] Version bumped in `src/vision_ai/__init__.py` and `pyproject.toml`
- [ ] Tested on a real PC: move, tap, drag, scroll, zoom, right click, pause, quit
- [ ] Installer + .exe signed
- [ ] `docs/TASKS.md` updated
