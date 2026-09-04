# Numpad Macro Pad — Windows Build Guide
### Turn your numlock-off numpad into a Stream Deck-style control surface

---

## Table of Contents

1. [How It Works](#how-it-works)
2. [Architecture Overview](#architecture-overview)
3. [Key Mapping Reference](#key-mapping-reference)
4. [Tech Stack Decision](#tech-stack-decision)
5. [Phase 1 — Intercept Numpad Keys](#phase-1--intercept-numpad-keys)
6. [Phase 2 — Action Engine](#phase-2--action-engine)
7. [Phase 3 — GUI Editor](#phase-3--gui-editor)
8. [Phase 4 — Persistence & Config](#phase-4--persistence--config)
9. [Phase 5 — System Tray & Auto-start](#phase-5--system-tray--auto-start)
10. [Full Project Structure](#full-project-structure)
11. [Code Walkthrough](#code-walkthrough)
12. [Edge Cases & Gotchas](#edge-cases--gotchas)
13. [Roadmap Ideas](#roadmap-ideas)
14. [Feature: Push-to-Talk Live Dictation](#feature-push-to-talk-live-dictation)

---

## How It Works

When **NumLock is OFF**, the numpad keys stop producing digits and instead send navigation keycodes (`Home`, `End`, `PgUp`, `PgDn`, `Arrow keys`, `Insert`, `Delete`). These are distinct key codes that Windows exposes at the low-level keyboard hook layer.

The plan:
1. Install a **global low-level keyboard hook** (`WH_KEYBOARD_LL`) in Windows that fires for every keypress system-wide.
2. When it detects a numpad key with NumLock off, **suppress the original key event** (so it doesn't reach other apps) and **fire your custom action** instead.
3. A **GUI editor** lets you visually assign actions to each of the 9 numpad positions.
4. Config is stored as a **JSON file** and read at startup.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                   Windows Kernel                    │
│         (Raw keyboard input via HID driver)         │
└────────────────────┬────────────────────────────────┘
                     │ WH_KEYBOARD_LL hook
┌────────────────────▼────────────────────────────────┐
│              Hook Handler (Python)                  │
│  • Detects numpad key + NumLock OFF                 │
│  • Suppresses original event                        │
│  • Looks up action in config                        │
│  • Dispatches to Action Engine                      │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│               Action Engine                         │
│  • launch_app(path)                                 │
│  • send_hotkey(keys)                                │
│  • run_script(path)                                 │
│  • set_volume(delta) / set_brightness(delta)        │
└────────────────────────────────────────────────────-┘
                     ▲
┌────────────────────┴────────────────────────────────┐
│              GUI Editor (Tkinter/PyQt)              │
│  • Visual 3×3 grid matching numpad layout           │
│  • Click a key → assign action from dropdown        │
│  • Saves to config.json                             │
└─────────────────────────────────────────────────────┘
                     ▲
┌────────────────────┴────────────────────────────────┐
│           System Tray Icon (pystray)                │
│  • Runs silently in background                      │
│  • Right-click → Open Editor / Quit                 │
│  • Auto-starts with Windows (optional)              │
└─────────────────────────────────────────────────────┘
```

---

## Key Mapping Reference

When NumLock is OFF, these are the virtual key codes the hook receives:

| Numpad Physical Key | VK Code | Sends (NumLock OFF) | Position |
|---|---|---|---|
| Numpad 7 | `VK_NUMPAD7` | `VK_HOME` (0x24) | Top-Left |
| Numpad 8 | `VK_NUMPAD8` | `VK_UP` (0x26) | Top-Center |
| Numpad 9 | `VK_NUMPAD9` | `VK_PRIOR` / PgUp (0x21) | Top-Right |
| Numpad 4 | `VK_NUMPAD4` | `VK_LEFT` (0x25) | Mid-Left |
| Numpad 5 | `VK_NUMPAD5` | `VK_CLEAR` (0x0C) | Center |
| Numpad 6 | `VK_NUMPAD6` | `VK_RIGHT` (0x27) | Mid-Right |
| Numpad 1 | `VK_NUMPAD1` | `VK_END` (0x23) | Bot-Left |
| Numpad 2 | `VK_NUMPAD2` | `VK_DOWN` (0x28) | Bot-Center |
| Numpad 3 | `VK_NUMPAD3` | `VK_NEXT` / PgDn (0x22) | Bot-Right |
| Numpad 0 | `VK_NUMPAD0` | `VK_INSERT` (0x2D) | Extra-1 |
| Numpad . | `VK_DECIMAL` | `VK_DELETE` (0x2E) | Extra-2 |

> **Detection trick:** The low-level hook provides `scanCode` and an `extended` flag. Numpad keys have `extended = False` and specific scan codes, which lets you distinguish them from the main keyboard arrow keys (which are `extended = True`).

---

## Tech Stack Decision

| Concern | Choice | Reason |
|---|---|---|
| Language | **Python 3.11+** | Rich ecosystem for Windows hooks, fast iteration |
| Key hook | **`keyboard` library** or **`pywin32` (WH_KEYBOARD_LL)** | `keyboard` is simpler; `pywin32` gives more control |
| GUI | **PyQt6** | Native-looking, easy grid layout, good for a visual editor |
| System tray | **`pystray`** | Simple cross-platform tray icon |
| Config | **JSON** | Human-readable, easy to edit manually too |
| Packaging | **PyInstaller** | Single `.exe`, no Python install needed |
| Volume control | **`pycaw`** | Wraps Windows Core Audio API |
| Brightness | **`screen-brightness-control`** | Works for most monitors |
| Hotkeys | **`pyautogui`** or **`keyboard`** | Send synthetic keystrokes |
| App launch | **`subprocess`** | Built-in, reliable |

### Install all dependencies

```bash
pip install keyboard pywin32 PyQt6 pystray pycaw screen-brightness-control pyautogui Pillow
```

---

## Phase 1 — Intercept Numpad Keys

This is the core of the whole system. We use `keyboard` library's hook with a filter.

### `hook.py`

```python
import keyboard
import ctypes

# Map of (vk_code, extended_flag) → logical numpad position name
NUMPAD_MAP = {
    (0x24, False): "num7",   # Home
    (0x26, False): "num8",   # Up
    (0x21, False): "num9",   # PgUp
    (0x25, False): "num4",   # Left
    (0x0C, False): "num5",   # Clear
    (0x27, False): "num6",   # Right
    (0x23, False): "num1",   # End
    (0x28, False): "num2",   # Down
    (0x22, False): "num3",   # PgDn
    (0x2D, False): "num0",   # Insert
    (0x2E, False): "numdot", # Delete
}

def is_numlock_off():
    return not ctypes.windll.user32.GetKeyState(0x90) & 1

def make_hook(config, action_engine):
    def on_key(event):
        if event.event_type != keyboard.KEY_DOWN:
            return
        if not is_numlock_off():
            return

        key = (event.vk, event.is_extended)
        if key in NUMPAD_MAP:
            position = NUMPAD_MAP[key]
            action = config.get_action(position)
            if action:
                action_engine.dispatch(action)
                return False  # suppress original keystroke
    return on_key

def start_hook(config, action_engine):
    hook_fn = make_hook(config, action_engine)
    keyboard.hook(hook_fn, suppress=False)
    # For full suppression, use low-level hook via pywin32 (see advanced section)
    keyboard.wait()
```

> **Note on suppression:** The `keyboard` library's `suppress=True` is all-or-nothing. For per-key suppression, use `pywin32`'s `SetWindowsHookEx(WH_KEYBOARD_LL)` and return `1` from the callback for keys you want to block. See the advanced section in Phase 1b below.

### Phase 1b — pywin32 Low-Level Hook (Full Suppression)

```python
import ctypes
import ctypes.wintypes as wintypes

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100

LLKHF_EXTENDED = 0x01

class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode",      wintypes.DWORD),
        ("scanCode",    wintypes.DWORD),
        ("flags",       wintypes.DWORD),
        ("time",        wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    ]

def install_hook(config, action_engine):
    HOOKPROC = ctypes.WINFUNCTYPE(
        ctypes.c_int, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
    )

    def low_level_handler(nCode, wParam, lParam):
        if nCode >= 0 and wParam == WM_KEYDOWN:
            kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            extended = bool(kb.flags & LLKHF_EXTENDED)
            key = (kb.vkCode, extended)

            if is_numlock_off() and key in NUMPAD_MAP:
                position = NUMPAD_MAP[key]
                action = config.get_action(position)
                if action:
                    action_engine.dispatch(action)
                    return 1  # Block the keystroke

        return ctypes.windll.user32.CallNextHookEx(hook, nCode, wParam, lParam)

    callback = HOOKPROC(low_level_handler)
    hook = ctypes.windll.user32.SetWindowsHookExW(
        WH_KEYBOARD_LL, callback, None, 0
    )

    # Message pump — required to keep hook alive
    msg = wintypes.MSG()
    while ctypes.windll.user32.GetMessageW(ctypes.byref(msg), None, 0, 0):
        ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
        ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))
```

---

## Phase 2 — Action Engine

Handles all four action types. Each action in config is a dict like:
```json
{ "type": "hotkey", "value": "ctrl+c" }
{ "type": "launch", "value": "C:\\Program Files\\Spotify\\Spotify.exe" }
{ "type": "script", "value": "C:\\scripts\\toggle_dark_mode.ps1" }
{ "type": "volume", "value": "+10" }
{ "type": "brightness", "value": "-20" }
```

### `actions.py`

```python
import subprocess
import pyautogui
import screen_brightness_control as sbc
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from comtypes import CLSCTX_ALL
import ctypes

class ActionEngine:

    def dispatch(self, action: dict):
        t = action.get("type")
        v = action.get("value", "")

        if t == "hotkey":
            self.send_hotkey(v)
        elif t == "launch":
            self.launch_app(v)
        elif t == "script":
            self.run_script(v)
        elif t == "volume":
            self.adjust_volume(int(v))
        elif t == "brightness":
            self.adjust_brightness(int(v))

    def send_hotkey(self, keys: str):
        # e.g. "ctrl+shift+t"
        pyautogui.hotkey(*keys.split("+"))

    def launch_app(self, path: str):
        subprocess.Popen([path], shell=True)

    def run_script(self, path: str):
        if path.endswith(".ps1"):
            subprocess.Popen(["powershell", "-ExecutionPolicy", "Bypass", "-File", path])
        elif path.endswith(".bat") or path.endswith(".cmd"):
            subprocess.Popen([path], shell=True)
        elif path.endswith(".py"):
            subprocess.Popen(["python", path])

    def adjust_volume(self, delta: int):
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = interface.QueryInterface(IAudioEndpointVolume)
        current = volume.GetMasterVolumeLevelScalar()
        new_vol = max(0.0, min(1.0, current + delta / 100.0))
        volume.SetMasterVolumeLevelScalar(new_vol, None)

    def adjust_brightness(self, delta: int):
        current = sbc.get_brightness()[0]
        sbc.set_brightness(max(0, min(100, current + delta)))
```

---

## Phase 3 — GUI Editor

A visual 3×3 grid (+ extras) where you click a button to configure that numpad key.

### `gui.py` (PyQt6)

```python
from PyQt6.QtWidgets import (
    QApplication, QWidget, QGridLayout, QPushButton,
    QDialog, QVBoxLayout, QComboBox, QLineEdit, QLabel,
    QFileDialog, QDialogButtonBox
)
from PyQt6.QtCore import Qt
import sys

POSITIONS = [
    ("num7", "7 / Home"),  ("num8", "8 / ↑"),   ("num9", "9 / PgUp"),
    ("num4", "4 / ←"),     ("num5", "5"),         ("num6", "6 / →"),
    ("num1", "1 / End"),   ("num2", "2 / ↓"),    ("num3", "3 / PgDn"),
    ("num0", "0 / Ins"),   ("numdot", ". / Del"),
]

class ActionDialog(QDialog):
    """Popup to configure a single key's action."""
    def __init__(self, current_action: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Assign Action")
        self.action = current_action.copy() if current_action else {}

        layout = QVBoxLayout()

        self.type_combo = QComboBox()
        self.type_combo.addItems(["hotkey", "launch", "script", "volume", "brightness"])
        if "type" in self.action:
            self.type_combo.setCurrentText(self.action["type"])
        layout.addWidget(QLabel("Action Type:"))
        layout.addWidget(self.type_combo)

        self.value_input = QLineEdit(self.action.get("value", ""))
        self.value_input.setPlaceholderText(
            "e.g. ctrl+shift+t  |  C:\\app.exe  |  +10  |  -20"
        )
        layout.addWidget(QLabel("Value:"))
        layout.addWidget(self.value_input)

        browse_btn = QPushButton("Browse file…")
        browse_btn.clicked.connect(self.browse)
        layout.addWidget(browse_btn)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select file")
        if path:
            self.value_input.setText(path)

    def get_action(self):
        return {
            "type": self.type_combo.currentText(),
            "value": self.value_input.text(),
        }


class NumpadEditor(QWidget):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.setWindowTitle("Numpad Macro Pad")
        self.setFixedSize(320, 280)
        self.build_grid()

    def build_grid(self):
        grid = QGridLayout()
        grid.setSpacing(8)
        positions_grid = [
            [("num7","7"), ("num8","8"), ("num9","9")],
            [("num4","4"), ("num5","5"), ("num6","6")],
            [("num1","1"), ("num2","2"), ("num3","3")],
        ]
        for row_i, row in enumerate(positions_grid):
            for col_i, (pos_id, label) in enumerate(row):
                btn = self._make_key_button(pos_id, label)
                grid.addWidget(btn, row_i, col_i)

        # Bottom row: 0 spans 2 cols, dot is 1 col
        btn0 = self._make_key_button("num0", "0")
        btndot = self._make_key_button("numdot", ".")
        grid.addWidget(btn0, 3, 0, 1, 2)
        grid.addWidget(btndot, 3, 2)

        self.setLayout(grid)

    def _make_key_button(self, pos_id, label):
        action = self.config.get_action(pos_id)
        subtitle = action.get("value", "— unassigned —") if action else "— unassigned —"
        btn = QPushButton(f"{label}\n{subtitle[:20]}")
        btn.setFixedHeight(60)
        btn.setStyleSheet("""
            QPushButton {
                background: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                font-size: 11px;
            }
            QPushButton:hover { background: #313244; }
            QPushButton[assigned=true] { border-color: #f97316; color: #f97316; }
        """)
        if action:
            btn.setProperty("assigned", True)
        btn.clicked.connect(lambda _, p=pos_id, b=btn: self.on_key_click(p, b))
        return btn

    def on_key_click(self, pos_id, btn):
        current = self.config.get_action(pos_id)
        dlg = ActionDialog(current, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_action = dlg.get_action()
            self.config.set_action(pos_id, new_action)
            self.config.save()
            # Refresh button label
            btn.setText(f"{pos_id[-1]}\n{new_action['value'][:20]}")
```

---

## Phase 4 — Persistence & Config

### `config.py`

```python
import json
import os

DEFAULT_CONFIG_PATH = os.path.join(
    os.getenv("APPDATA"), "NumpadMacroPad", "config.json"
)

class Config:
    def __init__(self, path=DEFAULT_CONFIG_PATH):
        self.path = path
        self.data = {}
        self.load()

    def load(self):
        if os.path.exists(self.path):
            with open(self.path, "r") as f:
                self.data = json.load(f)
        else:
            self.data = {"keys": {}}

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=2)

    def get_action(self, pos_id: str) -> dict | None:
        return self.data.get("keys", {}).get(pos_id)

    def set_action(self, pos_id: str, action: dict):
        self.data.setdefault("keys", {})[pos_id] = action
```

### Example `config.json`

```json
{
  "keys": {
    "num7": { "type": "launch",     "value": "C:\\Windows\\explorer.exe" },
    "num8": { "type": "hotkey",     "value": "ctrl+shift+t" },
    "num9": { "type": "volume",     "value": "+10" },
    "num4": { "type": "launch",     "value": "C:\\Program Files\\Spotify\\Spotify.exe" },
    "num5": { "type": "hotkey",     "value": "win+d" },
    "num6": { "type": "volume",     "value": "-10" },
    "num1": { "type": "script",     "value": "C:\\scripts\\dark_mode.ps1" },
    "num2": { "type": "brightness", "value": "-20" },
    "num3": { "type": "brightness", "value": "+20" }
  }
}
```

---

## Phase 5 — System Tray & Auto-start

### `tray.py`

```python
import pystray
from PIL import Image, ImageDraw
import threading

def make_icon():
    img = Image.new("RGB", (64, 64), color="#0f0f23")
    draw = ImageDraw.Draw(img)
    draw.rectangle([10,10,54,54], outline="#f97316", width=3)
    draw.text((20, 20), "NP", fill="#f97316")
    return img

def start_tray(editor_fn, quit_fn):
    icon = pystray.Icon(
        "NumpadMacroPad",
        make_icon(),
        "Numpad Macro Pad",
        menu=pystray.Menu(
            pystray.MenuItem("Open Editor", editor_fn),
            pystray.MenuItem("Quit", quit_fn),
        )
    )
    icon.run()
```

### `main.py` — Entry Point

```python
import threading
from config import Config
from actions import ActionEngine
from hook import install_hook
from tray import start_tray
from PyQt6.QtWidgets import QApplication
from gui import NumpadEditor
import sys

def main():
    config = Config()
    engine = ActionEngine()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # keep running when editor closes

    editor_window = NumpadEditor(config)

    def show_editor(_=None):
        editor_window.show()
        editor_window.raise_()

    def quit_app(_=None):
        app.quit()

    # Hook runs in background thread
    hook_thread = threading.Thread(
        target=install_hook, args=(config, engine), daemon=True
    )
    hook_thread.start()

    # Tray runs in background thread
    tray_thread = threading.Thread(
        target=start_tray, args=(show_editor, quit_app), daemon=True
    )
    tray_thread.start()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
```

### Auto-start with Windows

Add the app to the Windows startup registry:

```python
import winreg

def enable_autostart(exe_path: str):
    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0, winreg.KEY_SET_VALUE
    )
    winreg.SetValueEx(key, "NumpadMacroPad", 0, winreg.REG_SZ, exe_path)
    winreg.CloseKey(key)
```

---

## Full Project Structure

```
numpad-macropad/
├── main.py            # Entry point
├── hook.py            # WH_KEYBOARD_LL intercept
├── actions.py         # All action types
├── config.py          # JSON config load/save
├── gui.py             # PyQt6 visual editor
├── tray.py            # System tray icon
├── assets/
│   └── icon.png       # Tray icon
├── requirements.txt
└── build.spec         # PyInstaller spec
```

### `requirements.txt`

```
keyboard
pywin32
PyQt6
pystray
pycaw
screen-brightness-control
pyautogui
Pillow
comtypes
```

### Build to `.exe`

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --icon=assets/icon.ico --name NumpadMacroPad main.py
```

---

## Code Walkthrough

Here is the full end-to-end flow when you press **Numpad 9** (PgUp) with NumLock off:

```
User presses Numpad 9
        │
        ▼
Windows sends VK_PRIOR (0x21), extended=False to all hooks
        │
        ▼
WH_KEYBOARD_LL fires our callback
        │
        ├─ is_numlock_off()? → YES
        ├─ (0x21, False) in NUMPAD_MAP? → "num9"
        ├─ config.get_action("num9") → { type: "volume", value: "+10" }
        │
        ▼
ActionEngine.dispatch({ type: "volume", value: "+10" })
        │
        ▼
adjust_volume(+10) → pycaw raises master volume by 10%
        │
        ▼
Hook returns 1 → original PgUp keystroke is suppressed
```

---

## Edge Cases & Gotchas

| Issue | Solution |
|---|---|
| NumLock toggled mid-use | Always re-check `GetKeyState(0x90)` on each keypress, not cached |
| Arrow keys on main keyboard also trigger | Check `extended` flag — main keyboard arrows are `extended=True`, numpad are `False` |
| App launched as admin, hook doesn't fire | Run the app as admin too, or use `uiAccess=True` in the manifest |
| pyautogui can't type in UAC windows | That's a Windows security boundary — unfixable by design |
| Multiple monitors for brightness | `screen-brightness-control` returns a list; control all or just primary |
| Script runs with a console flash | Use `subprocess.Popen(..., creationflags=subprocess.CREATE_NO_WINDOW)` |
| App icon missing in tray on some systems | Ship a proper `.ico` file, not `.png`; use `Pillow` to convert |

---

## Roadmap Ideas

- **Key combos** — Numpad key + modifier (e.g. `Shift+Num7` = different action)
- **Profiles** — Switch between profiles (Gaming / Work / Streaming) via the tray
- **Visual feedback** — Overlay notification (like a tiny toast) on each key press
- **Drag-and-drop actions** in the editor
- **Import/export** config as JSON from the GUI
- **OBS integration** — trigger scene switches via OBS WebSocket
- **Text expansion** — Numpad key pastes a text snippet
- **Web dashboard** — Configure over localhost with a browser UI

---

---

## Feature: Push-to-Talk Live Dictation

Assign any numpad key to **dictation mode**: hold the key → mic opens → Whisper transcribes in real-time → words appear live in whatever window your cursor is in → release key → mic closes. Exactly like macOS dictation.

---

### How It Works (Architecture)

```
User holds Numpad key
        │
        ▼
Hook detects KEY_DOWN, action type = "ptt"
        │
        ▼
PTTEngine.start()
  ├── Opens PyAudio mic stream (16kHz, mono)
  ├── Spawns StreamingTranscriber thread
  │     ├── Buffers ~300ms audio chunks
  │     ├── Feeds chunks to faster-whisper streaming
  │     └── On each new word/phrase:
  │           └── TypeWriter.append(text) → pyautogui.typewrite()
  └── Shows floating overlay: 🎙 Recording...

User releases Numpad key
        │
        ▼
Hook detects KEY_UP, action type = "ptt"
        │
        ▼
PTTEngine.stop()
  ├── Signals mic thread to stop
  ├── Flushes remaining audio buffer → final transcription
  ├── Types any remaining text into active window
  └── Hides overlay
```

The key insight for "live as you speak": instead of waiting for silence, we use **`faster-whisper`'s VAD (Voice Activity Detection)** to detect word boundaries and flush partial results every ~300ms, typing each chunk immediately.

---

### Dependencies

```bash
pip install faster-whisper pyaudio pyautogui PyQt6
```

> **`faster-whisper`** is a re-implementation of OpenAI Whisper using CTranslate2 — 4× faster and uses ~70% less RAM than the original `whisper` package, with identical accuracy. It also supports streaming via chunked inference.

**Download the Whisper model once** (runs offline after this):

```python
from faster_whisper import WhisperModel
# Downloads ~150MB to ~/.cache/huggingface/ on first run
# Options: "tiny", "base", "small", "medium", "large-v3"
# Recommended: "base" for speed, "small" for accuracy
model = WhisperModel("base", device="cpu", compute_type="int8")
```

> On a mid-range CPU, `base` transcribes in roughly real-time. Use `"small"` if you have a GPU (`device="cuda"`).

---

### `ptt_engine.py` — Core PTT Logic

```python
import threading
import queue
import time
import numpy as np
import pyaudio
import pyautogui
from faster_whisper import WhisperModel

SAMPLE_RATE   = 16000
CHUNK_FRAMES  = 512          # ~32ms per chunk
FLUSH_SECONDS = 0.4          # transcribe every 400ms of audio
MIN_AUDIO_RMS = 100          # ignore silence below this amplitude

class PTTEngine:
    """
    Hold-to-talk dictation engine.
    Call start() on key down, stop() on key up.
    """

    def __init__(self, model_size="base", overlay=None):
        # Load model once at startup — NOT on each keypress
        print("[PTT] Loading Whisper model...")
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        print("[PTT] Model ready.")

        self.overlay  = overlay       # optional floating UI widget
        self._running = False
        self._audio_q = queue.Queue()
        self._mic_thread   = None
        self._trans_thread = None
        self._typed_so_far = ""       # track what we've already typed

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self):
        if self._running:
            return
        self._running       = True
        self._typed_so_far  = ""
        self._audio_q       = queue.Queue()

        if self.overlay:
            self.overlay.show_recording()

        self._mic_thread   = threading.Thread(target=self._mic_loop,   daemon=True)
        self._trans_thread = threading.Thread(target=self._trans_loop, daemon=True)
        self._mic_thread.start()
        self._trans_thread.start()

    def stop(self):
        if not self._running:
            return
        self._running = False
        # Sentinel to unblock transcriber
        self._audio_q.put(None)
        self._mic_thread.join(timeout=2)
        self._trans_thread.join(timeout=5)

        if self.overlay:
            self.overlay.hide()

    # ── Microphone thread ─────────────────────────────────────────────────────

    def _mic_loop(self):
        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_FRAMES,
        )
        try:
            while self._running:
                raw = stream.read(CHUNK_FRAMES, exception_on_overflow=False)
                self._audio_q.put(raw)
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()

    # ── Transcription thread ──────────────────────────────────────────────────

    def _trans_loop(self):
        flush_frames   = int(SAMPLE_RATE * FLUSH_SECONDS)
        buffer         = np.array([], dtype=np.int16)
        last_full_text = ""

        while True:
            # Collect audio up to flush_frames
            while len(buffer) < flush_frames:
                chunk = self._audio_q.get()
                if chunk is None:          # stop() signal
                    # Final flush
                    if len(buffer) > 0:
                        self._transcribe_and_type(buffer, last_full_text)
                    return
                arr = np.frombuffer(chunk, dtype=np.int16)
                buffer = np.concatenate([buffer, arr])

            # Transcribe the accumulated buffer
            last_full_text = self._transcribe_and_type(buffer, last_full_text)

            # Keep a 200ms overlap to avoid cutting words at boundaries
            overlap = int(SAMPLE_RATE * 0.2)
            buffer  = buffer[-overlap:]

    def _transcribe_and_type(self, audio_np: np.ndarray, already_typed: str) -> str:
        """
        Transcribe audio_np, then type only the NEW portion
        that hasn't been typed yet.
        """
        # Skip if silent
        rms = np.sqrt(np.mean(audio_np.astype(np.float32) ** 2))
        if rms < MIN_AUDIO_RMS:
            return already_typed

        # faster-whisper expects float32 in [-1, 1]
        audio_f32 = audio_np.astype(np.float32) / 32768.0

        segments, _ = self.model.transcribe(
            audio_f32,
            language="en",
            vad_filter=True,          # skip silence automatically
            beam_size=1,              # fastest decoding
            best_of=1,
        )
        full_text = " ".join(seg.text.strip() for seg in segments).strip()

        if not full_text:
            return already_typed

        # Type only the delta (new words not yet typed)
        new_text = _diff_suffix(already_typed, full_text)
        if new_text:
            _type_text(new_text)

        return full_text


# ── Helpers ───────────────────────────────────────────────────────────────────

def _diff_suffix(old: str, new: str) -> str:
    """
    Return the part of `new` that extends beyond `old`.
    e.g. old="hello world", new="hello world how are"
         → " how are"
    """
    if new.startswith(old):
        return new[len(old):]
    # Whisper sometimes revises earlier words; find longest common prefix
    words_old = old.split()
    words_new = new.split()
    i = 0
    for i, (a, b) in enumerate(zip(words_old, words_new)):
        if a != b:
            break
    else:
        i = min(len(words_old), len(words_new))
    return " " + " ".join(words_new[i:]) if i < len(words_new) else ""


def _type_text(text: str):
    """
    Type text into the active window using pyautogui.
    Uses clipboard paste for speed and Unicode support.
    """
    import win32clipboard
    import win32con

    # Clipboard-paste is faster than typewrite() and handles Unicode
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
    win32clipboard.CloseClipboard()

    pyautogui.hotkey("ctrl", "v")
```

> **Why clipboard paste instead of `typewrite()`?** `pyautogui.typewrite()` is slow character-by-character and breaks on non-ASCII characters. Pasting via clipboard is instant and handles any language Whisper outputs.

---

### `ptt_overlay.py` — Floating Recording Indicator

A small always-on-top pill that appears near the taskbar while recording — similar to the macOS dictation microphone bubble.

```python
from PyQt6.QtWidgets import QLabel, QApplication
from PyQt6.QtCore    import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui     import QFont

class OverlaySignals(QObject):
    show_sig = pyqtSignal()
    hide_sig = pyqtSignal()

class PTTOverlay(QLabel):
    """
    Floating pill: "🎙 Listening…" shown while key is held.
    Must be created on the Qt main thread.
    Call show_recording() / hide() from any thread.
    """

    def __init__(self):
        super().__init__("🎙  Listening…")
        self.signals = OverlaySignals()
        self.signals.show_sig.connect(self._show)
        self.signals.hide_sig.connect(self._hide)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("""
            QLabel {
                background: #f97316;
                color: #ffffff;
                border-radius: 14px;
                padding: 6px 18px;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        self.adjustSize()
        self._position_bottom_center()

    def _position_bottom_center(self):
        screen = QApplication.primaryScreen().geometry()
        self.move(
            screen.center().x() - self.width() // 2,
            screen.bottom() - 80
        )

    def show_recording(self):
        self.signals.show_sig.emit()   # thread-safe

    def hide(self):
        self.signals.hide_sig.emit()

    def _show(self):
        self._position_bottom_center()
        super().show()
        self.raise_()

    def _hide(self):
        super().hide()
```

---

### Wiring PTT into the Action Engine

Add a new action type `"ptt"` to `actions.py`:

```python
# In actions.py — add to __init__
from ptt_engine import PTTEngine
from ptt_overlay import PTTOverlay

class ActionEngine:
    def __init__(self):
        self.overlay    = PTTOverlay()   # created on main Qt thread
        self.ptt_engine = PTTEngine(model_size="base", overlay=self.overlay)

    def dispatch(self, action: dict, event_type: str = "down"):
        t = action.get("type")
        v = action.get("value", "")

        if t == "ptt":
            if event_type == "down":
                self.ptt_engine.start()
            else:                          # key up
                self.ptt_engine.stop()
            return

        # ... existing action types unchanged
```

Update the hook to also pass `KEY_UP` events for PTT keys:

```python
# In hook.py low_level_handler — extend to handle KEY_UP
WM_KEYUP   = 0x0101
WM_SYSKEYUP = 0x0105

def low_level_handler(nCode, wParam, lParam):
    if nCode >= 0:
        kb  = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
        extended = bool(kb.flags & LLKHF_EXTENDED)
        key = (kb.vkCode, extended)

        if is_numlock_off() and key in NUMPAD_MAP:
            position = NUMPAD_MAP[key]
            action   = config.get_action(position)

            if action:
                is_down = wParam in (WM_KEYDOWN,)
                is_up   = wParam in (WM_KEYUP, WM_SYSKEYUP)

                if action.get("type") == "ptt":
                    # Fire on both down and up
                    if is_down or is_up:
                        event_type = "down" if is_down else "up"
                        action_engine.dispatch(action, event_type=event_type)
                        return 1   # suppress

                elif is_down:
                    action_engine.dispatch(action)
                    return 1

    return ctypes.windll.user32.CallNextHookEx(hook, nCode, wParam, lParam)
```

---

### Config for PTT

In the GUI editor, PTT appears as a new action type in the dropdown. The `value` field lets you pick the Whisper model size.

```json
{
  "keys": {
    "num0": { "type": "ptt", "value": "base" }
  }
}
```

In the editor's `ActionDialog`, add a helpful note when `"ptt"` is selected:

```python
# In gui.py ActionDialog — add a dynamic hint label
def on_type_changed(self, t):
    hints = {
        "ptt":        "Value = Whisper model: tiny / base / small / medium",
        "hotkey":     "Value = e.g.  ctrl+shift+t",
        "launch":     "Value = full path to .exe or file",
        "script":     "Value = path to .ps1 / .bat / .py",
        "volume":     "Value = e.g.  +10  or  -10",
        "brightness": "Value = e.g.  +20  or  -20",
    }
    self.hint_label.setText(hints.get(t, ""))
```

---

### PTT Flow Diagram

```
KEY_DOWN (num0)
    │
    ▼
ptt_engine.start()
    │
    ├──[Mic thread]──► PyAudio 16kHz stream
    │                       │
    │                       ▼ raw bytes every 32ms
    │                  audio_queue
    │                       │
    ├──[Trans thread]──◄─────┘
    │   • Accumulate 400ms of audio
    │   • faster-whisper.transcribe() with VAD
    │   • Diff against already-typed text
    │   • Paste delta via clipboard → active window
    │   • Loop
    │
    └──[Qt main]──► PTTOverlay shown ("🎙 Listening…")

KEY_UP (num0)
    │
    ▼
ptt_engine.stop()
    │
    ├── Sends None sentinel to audio_queue
    ├── Trans thread: final flush → type remaining words
    ├── Threads join
    └── PTTOverlay hidden
```

---

### Performance Tuning

| Scenario | Recommended settings |
|---|---|
| Fast laptop / low latency | `model="tiny"`, `FLUSH_SECONDS=0.3` |
| Balanced (default) | `model="base"`, `FLUSH_SECONDS=0.4` |
| High accuracy, GPU available | `model="small"`, `device="cuda"`, `FLUSH_SECONDS=0.3` |
| Slow CPU | `model="tiny"`, `FLUSH_SECONDS=0.6`, `beam_size=1` |

> **First keypress delay:** Whisper model loads at app startup, not on first press — so there's zero delay when you push the key.

---

### New Dependencies for PTT

Add to `requirements.txt`:

```
faster-whisper
pyaudio
pywin32        # already listed — used for clipboard paste
```

> **PyAudio on Windows:** If `pip install pyaudio` fails, use the prebuilt wheel:
> ```bash
> pip install pipwin
> pipwin install pyaudio
> ```

---

### Updated Project Structure

```
numpad-macropad/
├── main.py
├── hook.py
├── actions.py
├── config.py
├── gui.py
├── tray.py
├── ptt_engine.py      ← NEW: Whisper streaming transcriber
├── ptt_overlay.py     ← NEW: Floating recording indicator
├── assets/
│   └── icon.png
├── requirements.txt
└── build.spec
```
-e 
---

*Built for Windows 10/11 · Python 3.11+ · MIT License*
