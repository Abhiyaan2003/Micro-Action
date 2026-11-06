# Contributing to KeySpark

Thanks for taking the time to contribute! This guide covers everything you need to go from zero to a merged pull request.

---

## Table of Contents

1. [Run it locally](#1-run-it-locally)
2. [Run the tests](#2-run-the-tests)
3. [Build the standalone EXE](#3-build-the-standalone-exe)
4. [Open a pull request](#4-open-a-pull-request)
5. [Code style](#5-code-style)
6. [Reporting bugs](#6-reporting-bugs)

---

## 1 · Run it locally

**Prerequisites**: Windows 10/11 (64-bit) · Python 3.12+ · a microphone (for Speech-to-Text)

```powershell
# 1. Clone
git clone https://github.com/Abhiyaan2003/KeySpark.git
cd KeySpark

# 2. Create a virtual environment and install dependencies
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# 3. Launch the app (no hook, GUI-only preview)
python dev_preview.py

# 4. Launch the full app (requires NumLock key on the numpad)
python main.py
```

> **Tip**: `dev_preview.py` opens the Glass editor without starting the low-level keyboard hook or action engines — perfect for iterating on the UI without side-effects.

---

## 2 · Run the tests

```powershell
# From the repo root, with the venv active
python -m pytest tests/ -v --tb=short
```

The `tests/` directory contains:

| File | What it covers |
|------|----------------|
| `test_hook.py` | Low-level keyboard hook interception logic |
| `test_ptt.py` | Push-to-talk / Whisper engine |
| `test_screen_capture.py` | Screenshot & screen recording engine |
| `test_all_possibilities.py` | Action dispatch coverage |

Add a test for every bug fix and every new action type you introduce.

---

## 3 · Build the standalone EXE

```powershell
pip install pyinstaller
pyinstaller KeySpark.spec --noconfirm
```

The compiled binary lands at `dist/KeySpark/KeySpark.exe`.  
The spec file (`KeySpark.spec`) is the single source of truth for packaging — edit it if you add new data files or hidden imports.

---

## 4 · Open a pull request

1. **Fork** the repo on GitHub.
2. **Create a branch** from `main` with a descriptive name:
   ```bash
   git checkout -b fix/ptt-crash-on-empty-audio
   ```
3. **Make your changes**, write or update tests, and confirm `pytest` passes.
4. **Push** to your fork and **open a PR** against `main`.
5. Fill in the PR template — describe what changed and why, and link any related issue (`Closes #42`).

A maintainer will review within a few days. Small, focused PRs merge fastest.

---

## 5 · Code style

- **Python 3.12** throughout; type annotations are encouraged.
- Keep the existing `pyrightconfig.json` happy — run `pyright` if you have it installed.
- No external formatter is enforced yet, but please match the surrounding style (4-space indents, single quotes for strings in Qt code, f-strings preferred).
- Keep each module focused on its single responsibility (hook, action dispatch, UI, engine — do not mix layers).

---

## 6 · Reporting bugs

Please use the [Bug Report issue template](https://github.com/Abhiyaan2003/KeySpark/issues/new?template=bug_report.yml).  
Include:
- Windows version
- Python version (if running from source)
- Steps to reproduce
- What you expected vs. what happened
- Logs from the terminal or the system tray tooltip if relevant

---

Questions? Start a [Discussion](https://github.com/Abhiyaan2003/KeySpark/discussions) rather than opening an issue — it keeps the issue tracker for bugs and features only.

