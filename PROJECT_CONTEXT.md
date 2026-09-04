# Micro Action — Complete System Context & Architecture Guide

## 1. Executive Summary

**Micro Action** is a high-performance Windows background utility that transforms any standard physical numeric keyboard keypad into an active, custom hardware macro controller (similar to a Stream Deck). 

Operating silently in the system tray, it intercepts numpad keypresses when **NumLock is OFF**, suppressing default navigation keystrokes and executing customizable automated actions. Beyond basic shortcuts and app launching, Micro Action features a built-in offline **Whisper Push-to-Talk (PTT)** speech-to-text engine and a full **Screen Capture & Recording Engine**.

The visual GUI editor follows a **Neo-Brutalist** design language with 1:1 hardware keycap mapping, heavy black ink outlines, solid offset drop shadows, and neon action color coding.

---

## 2. Core Capabilities & Action Types

Micro Action supports seven distinct action types assignable to any of the 11 numpad positions (`num7`, `num8`, `num9`, `num4`, `num5`, `num6`, `num1`, `num2`, `num3`, `num0`, `numdot`):

| Action Type | Icon | Color Accent | Description | Parameter Format |
|---|---|---|---|---|
| **Web Link** | 🌐 `WEB` | Stark Yellow (`#ffe359`) | Opens URLs in default web browser | `https://example.com` |
| **Hotkey** | ⚡ `HOTKEY` | Hotkey Blue (`#80b3ff`) | Sends synthetic key combinations | `ctrl+shift+t` |
| **Launch App** | 🚀 `LAUNCH` | Launch Pink (`#ff9fbc`) | Launches executable applications | `C:\Windows\explorer.exe` |
| **Script** | 📜 `SCRIPT` | Script Green (`#58d68d`) | Executes scripts in background | `path/to/script.ps1` (`.ps1`, `.bat`, `.cmd`, `.py`) |
| **Push-to-Talk** | 🎙️ `PTT` | PTT Orange (`#ff9f1c`) | Hold key to record voice with live transcription preview | `tiny`, `base`, `small`, `medium`, `large-v3` |
| **Screenshot** | 📸 `SCREENSHOT` | Cyan (`#00f0ff`) | Captures screen to disk and/or clipboard with audio/visual flash feedback | `mode|clipboard=true|save=true` |
| **Screen Record** | 🎥 `SCREENREC` | Red (`#ff4d4d`) | Toggles video recording of screen | `mode|fps=15` |
| **Volume / Brightness** | 🔊 / ☀️ | System Gray | Adjusts Windows master volume or monitor brightness | Delta percentage (`+10`, `-10`) |

---

## 3. Architecture & System Data Flow

```
┌────────────────────────────────────────────────────────────────────────┐
│                         Windows OS Kernel                              │
│                (Raw Keyboard HID Events & Sound Mixer)                 │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ WH_KEYBOARD_LL (ctypes)
┌───────────────────────────────────▼────────────────────────────────────┐
│                    Windows Low-Level Hook (`hook.py`)                   │
│  • Checks NumLock State (GetKeyState 0x90)                             │
│  • Verifies Extended Flag (Differentiates Numpad from Arrow keys)      │
│  • Suppresses original keystroke on KEY_DOWN                           │
│  • Dispatches KEY_DOWN & KEY_UP signals                                │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                  Action Engine (`actions.py`)                          │
│  • Dispatches URL launch, Hotkey, App Execution, Script Run            │
│  • Routes Speech-to-Text PTT start/stop to `PTTEngine`                 │
│  • Routes Screen Capture actions to `ScreenEngine`                     │
└──────────────────┬────────────────┬─────────────────┬──────────────────┘
                   │                │                 │
┌──────────────────▼──────┐ ┌───────▼─────────┐ ┌─────▼──────────────────┐
│ PTT Engine & Overlay    │ │ Screen Engine   │ │ Qt Main GUI Window     │
│ (`ptt_engine.py`)       │ │ (`screen_engine.py`)│ (`gui.py`)           │
│ • PyAudio 16kHz Stream  │ │ • mss capture   │ │ • Neo-Brutalist Grid   │
│ • faster-whisper (CTrans)│ │ • OpenCV video  │ │ • Single-Instance Mutex│
│ • Floating PTT Overlay  │ │ • Flash Overlay │ │ • Thread-safe Signals  │
└─────────────────────────┘ └─────────────────┘ └────────────────────────┘
```

### Key Detection & Disambiguation Algorithm
When NumLock is OFF, Windows sends standard navigation keycodes (`VK_HOME`, `VK_UP`, `VK_PRIOR`, `VK_LEFT`, etc.). To prevent hijacking the main keyboard arrow/navigation keys, `hook.py` inspects the `flags` field of `KBDLLHOOKSTRUCT`:
- Numpad Keys: `extended = False`
- Dedicated Navigation Arrow Keys: `extended = True`
- Interception rule: `if (not NumLock) and (not extended) and (VK in NUMPAD_MAP)` $\rightarrow$ Block original keystroke (`return 1`) and fire custom action.

---

## 4. Subsystem Component Breakdown

| Module | Responsibility | Key Technologies |
|---|---|---|
| `main.py` | Application entry point, single-instance named mutex, Qt event loop initialization, thread wiring | `PyQt6`, `win32event`, `win32api` |
| `gui.py` | Physical 3x3 keycap grid editor, custom action configuration dialogs, status badge indicator | `PyQt6` (QGridLayout, QDialog) |
| `hook.py` | Low-level C-level Windows keyboard hook callback, message loop pump thread | `ctypes`, `win32con`, `WH_KEYBOARD_LL` |
| `actions.py` | Central action dispatcher routing calls to OS APIs, PTT engine, or Screen engine | `pyautogui`, `subprocess`, `pycaw` |
| `config.py` | Persists JSON key mappings, PTT options, and capture settings | `json`, `os` |
| `ptt_engine.py` | Manages mic capture, 1.0s live transcription ticks, LocalAgreement word stabilization, and final release pass | `faster_whisper`, `pyaudio`, `win32clipboard` |
| `ptt_overlay.py` | Frameless, stay-on-top pill widget displaying live transcription preview (committed vs. tentative text) | `PyQt6` (Qt.WindowType.WindowStaysOnTopHint) |
| `screen_engine.py` | Handles fullscreen/monitor/window screenshot taking and background video recording | `mss`, `cv2` (OpenCV), `PIL`, `wave` |
| `flash_overlay.py` | Fullscreen translucent white flash overlay providing camera shutter visual feedback | `PyQt6` (QGraphicsOpacityEffect) |
| `tray.py` | System tray icon with context menu for showing main window or exiting | `pystray`, `Pillow` |

---

## 5. Design System: Neo-Brutalist Edition

The user interface follows the **Neo-Brutalist** visual style specified in `DESIGN.md`:

- **Primary Canvas**: Warm cardboard beige (`#f4f2ed`).
- **Containers**: Stark white plate (`#ffffff`) surrounded by `2px` or `3px` solid black borders (`#000000`).
- **Elevation**: Zero soft blurred shadows. All elevation uses flat solid offset drop shadows (`border-right: 5px solid #000; border-bottom: 5px solid #000;`).
- **Press Interaction**: Clicking buttons collapses the offset shadow to `2px` while applying top-left offset padding to mimic mechanical keypresses.
- **Typography**: Display/Keycap labels use heavy chunky typography (`Impact, Arial Black`), while subtext uses clean monospace (`Consolas`).

---

## 6. Project Directory Layout

```
Micro-Action/
├── main.py                   # App entry point & event loop
├── gui.py                    # Neo-Brutalist PyQt6 Editor UI
├── hook.py                   # Low-level Windows WH_KEYBOARD_LL hook
├── actions.py                # Action execution engine dispatcher
├── config.py                 # JSON configuration manager
├── ptt_engine.py             # Push-to-Talk speech-to-text engine
├── ptt_overlay.py            # Floating dictation overlay window
├── screen_engine.py          # Screenshot & screen recording engine
├── flash_overlay.py          # Screen capture shutter flash overlay
├── tray.py                   # System tray icon service
├── qt.conf                   # Qt environment configuration
├── MicroAction.spec          # PyInstaller bundle build specification
├── PRODUCT.md                # Product positioning & user context
├── DESIGN.md                 # Neo-Brutalist design tokens & specs
├── numpad-macropad-guide.md  # Architecture design guide reference
├── assets/                   # Static resources (icon.png, shutter.wav)
├── scripts/                  # Development & helper scripts
│   ├── fix_mic_volume.py
│   └── generate_shutter_sound.py
├── tests/                    # Integration & unit diagnostic tests
│   ├── test_e2e_ptt.py
│   ├── test_hook.py
│   ├── test_hook_debug.py
│   ├── test_ptt.py
│   ├── test_ptt_unit.py
│   └── test_screen_capture.py
└── dist/                     # Compiled PyInstaller executable bundle
```

---

## 7. Configuration Schema (`config.json`)

Configuration is saved in `%APPDATA%/NumpadMacroPad/config.json`:

```json
{
  "autostart": true,
  "keys": {
    "num7": { "type": "web", "value": "https://github.com" },
    "num8": { "type": "hotkey", "value": "ctrl+shift+t" },
    "num9": { "type": "screenshot", "value": "fullscreen|clipboard=true|save=true|sound=true" },
    "num4": { "type": "launch", "value": "C:\\Windows\\explorer.exe" },
    "num5": { "type": "ptt", "value": "base" },
    "num6": { "type": "screenrec", "value": "fullscreen|fps=15" }
  },
  "capture_settings": {
    "screenshot_dir": "C:\\Users\\User\\Pictures\\Screenshots",
    "recording_dir": "C:\\Users\\User\\Videos\\Captures"
  }
}
```

---

## 8. Build & Packaging Pipeline

The project is compiled into a standalone Windows executable using PyInstaller:

```bash
pyinstaller MicroAction.spec
```

`MicroAction.spec` configures single-folder bundling (`onefile=False` for fast startup), includes `assets/` and `qt.conf`, bundles PyAudio/OpenCV binaries, and sets `app_icon.ico` as the executable icon. `get_resource_path()` in code resolves assets seamlessly in both development mode and compiled `sys._MEIPASS` runtime.
