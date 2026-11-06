# Product

<!-- impeccable:product-schema 1 -->

## Platform

adaptive

## Stack
Python, PyQt6, pystray, pyautogui, ctypes.

## Users
Windows power users, developers, streamers, and professionals who want to reuse a standard numeric keyboard keypad as a custom hardware macropad without scripting or dedicated hardware.

## Product Purpose
Turn a standard keyboard numpad into an active macro controller. It runs silently in the system tray, intercepts keystrokes when NumLock is off, and maps them to user-defined actions (URLs, shortcuts, applications, scripts, or Whisper voice-to-text dictation).

## Positioning
A lightweight, zero-scripting visual utility to map physical numpad keys. Unlike general tools like AutoHotkey, it provides a visual 1:1 hardware key layout editor and features a built-in Whisper Push-to-Talk (PTT) transcription engine for instant hands-free typing.

## Operating Context
A native Windows background task minimizing to the system tray. System NumLock status governs behavior: NumLock Off activates custom macro bindings, while NumLock On passes keys through as standard numbers.

## Capabilities and Constraints
- **Keystroke Interception**: Low-level Windows keyboard hook (`WH_KEYBOARD_LL` via ctypes) captures numpad keys.
- **Autostart**: Automatic Windows startup registry integration.
- **PTT Whisper Engine**: Push-to-Talk speech-to-text transcribes voice directly to the active text cursor.
- **Keycap Grid Editor**: A custom PyQt6 GUI displaying the physical numpad layout for configuration.
- **Single Instance**: System-wide single-instance execution via a named mutex.

## Brand Commitments
- **Name**: KeySpark
- **Identity**: Dark-mode industrial, clean mechanical keyboard theme.

## Evidence on Hand
- Full implementation of PyQt6 visual editor in `gui.py`.
- Low-level hook logic in `hook.py`.
- Whisper PTT transcription overlay in `ptt_overlay.py` and engine in `ptt_engine.py`.

## Product Principles
- **Hardware-Aligned Visuals**: The UI layout must mimic physical keycaps to maintain a high level of user mapping.
- **Unobtrusive & Lightweight**: Low resource consumption, daemon thread execution, clean exit logic.
- **Tactile Feedback**: Clear visual indications of the active/inactive state of the keyboard hook (NumLock).
