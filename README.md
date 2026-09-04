# 🎛️ Micro Action — Physical Numpad Macro Engine

<p align="center">
  <img src="assets/icon.png" alt="Micro Action Logo" width="128" height="128" />
</p>

<p align="center">
  <b>Turn any standard $5 physical Numpad into an offline Stream Deck macro controller with zero extra hardware!</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/PyQt6-Neo--Brutalist-0ea5e9?style=for-the-badge&logo=qt&logoColor=white" alt="PyQt6 UI" />
  <img src="https://img.shields.io/badge/Whisper-Speech--to--Text-000000?style=for-the-badge&logo=openai&logoColor=white" alt="Whisper AI" />
  <img src="https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Windows" />
</p>

> [!IMPORTANT]
> ### ⚡ Instant Download (No Installation / No Python Required!)
> Download the pre-compiled, standalone Windows application directly from [**GitHub Releases**](https://github.com/Abhiyaan2003/Micro-Action/releases):
> 
> 📦 **[Download Latest Executable Release (v1.0.0)](https://github.com/Abhiyaan2003/Micro-Action/releases)**
> 1. Download `MicroAction-v1.0.0-windows-x64.zip`.
> 2. Extract the folder anywhere on your computer.
> 3. Double click **`MicroAction.exe`** to start using immediately!

---

## 🌟 Overview

**Micro Action** is a high-performance Windows desktop application designed to transform any standard physical USB or Bluetooth numeric keypad into a fully custom macro controller (Stream Deck alternative).

By hooking low-level Windows keyboard inputs via `WH_KEYBOARD_LL`, Micro Action selectively intercepts keypresses **only when `NumLock` is turned OFF**, leaving standard numeric typing when `NumLock` is ON 100% untouched.

---

## ✨ Key Features

- 🎙️ **Speech to Text (Offline Whisper AI)**: Hold a key to speak and automatically transcribe voice directly to your active cursor position using local `faster-whisper` (`base` model). Includes real-time floating visual overlay feedback.
- 🌐 **Web & App Launcher**: Instantly launch websites in your preferred browser (Chrome, Firefox, Edge, Brave) or open executables/scripts.
- ⌨️ **Global Hotkey Dispatcher**: Trigger complex keyboard combinations (e.g. `Ctrl+Shift+T`, `Win+D`, `Alt+Tab`) with a single keypress.
- 📸 **Screen Capture Engine**: Capture full screen, primary monitor, or active window snapshots complete with a custom visual shutter flash.
- 🎥 **Screen Recording Engine**: Record screen sessions directly with smooth MP4 output.
- 🎨 **Neo-Brutalist UI**: Modern high-contrast dark interface powered by **PyQt6** and vector **Hugeicons** keycap badges.
- 🤫 **Silent System Tray Operation**: Runs unobtrusively in the background with quick profile switching and tray controls.

---

## 🎹 Physical Numpad Mapping

Micro Action maps the **11 primary navigation keys** available on a standard numeric keypad when `NumLock` is **OFF**:

| Key Position | Virtual Key | Human Label | Default Purpose |
| :--- | :--- | :--- | :--- |
| **Num 7** | `VK_HOME` (0x24) | `7 / Home` | Customizable Macro |
| **Num 8** | `VK_UP` (0x26) | `8 / ↑` | Customizable Macro |
| **Num 9** | `VK_PRIOR` (0x21) | `9 / PgUp` | Customizable Macro |
| **Num 4** | `VK_LEFT` (0x25) | `4 / ←` | Customizable Macro |
| **Num 5** | `VK_CLEAR` (0x0C) | `5 / Clear` | Customizable Macro |
| **Num 6** | `VK_RIGHT` (0x27) | `6 / →` | Customizable Macro |
| **Num 1** | `VK_END` (0x23) | `1 / End` | Customizable Macro |
| **Num 2** | `VK_DOWN` (0x28) | `2 / ↓` | Customizable Macro |
| **Num 3** | `VK_NEXT` (0x22) | `3 / PgDn` | Customizable Macro |
| **Num 0** | `VK_INSERT` (0x2D) | `0 / Insert` | Speech to Text (STT) |
| **Num .** | `VK_DELETE` (0x2E) | `. / Delete` | Customizable Macro |

---

## ⚡ Supported Action Types

1. **Open Website**: Launch target URLs with custom browser choices (`Default`, `Chrome`, `Firefox`, `Edge`, `Brave`).
2. **Send Hotkey**: Send system hotkey sequences (`ctrl+shift+t`, `alt+f4`, `win+shift+s`).
3. **Launch Application**: Execute binaries or shortcuts (`.exe`, `.lnk`).
4. **Run Script**: Execute automation scripts (`.bat`, `.ps1`, `.py`).
5. **Speech to Text**: Offline Whisper voice dictation typed directly into focused input fields.
6. **Take Screenshot**: Instant screen grab with scope selection (`Full Screen`, `Active Window`, `Primary Monitor`).
7. **Screen Record**: Smooth video screen recorder with target region control.

---

## 📐 Architecture & How It Works

```mermaid
graph TD
    A[Physical Numpad Keypress] --> B{NumLock State?}
    B -- NumLock ON --> C[Standard Number Input]
    B -- NumLock OFF --> D[Low-Level Hook WH_KEYBOARD_LL]
    D --> E[Intercept & Suppress Default Nav Keystroke]
    E --> F[Lookup Assigned Action in config.json]
    F --> G{Action Type}
    G -- Website / App / Script --> H[Execute System Process]
    G -- Hotkey --> I[Simulate Win32 Key Sequence]
    G -- Speech to Text --> J[Capture Mic Audio -> Whisper Engine -> Type Text]
    G -- Screenshot / Record --> K[Screen Capture Engine -> Shutter Flash / Video]
```

---

## 💻 Developer Setup (Build from Source)

### Prerequisites

- **Windows 10 / 11** (64-bit)
- **Python 3.12+**
- Active microphone (for Speech to Text feature)

### Step-by-Step Build Instructions

1. **Clone repository**:
   ```bash
   git clone https://github.com/Abhiyaan2003/Micro-Action.git
   cd Micro-Action
   ```

2. **Create virtual environment & install dependencies**:
   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Run application locally**:
   ```bash
   python main.py
   ```

4. **Compile Standalone Executable**:
   ```bash
   pyinstaller MicroAction.spec --noconfirm
   ```
   *The standalone binary will be output to `dist/MicroAction/MicroAction.exe`.*

---

## 🛠️ Project Structure

```
Micro-Action/
├── main.py                  # Application entry point & Qt lifecycle
├── gui.py                   # PyQt6 Main Window & Numpad visual layout
├── hook.py                  # Windows WH_KEYBOARD_LL low-level input hook
├── ptt_engine.py            # Local faster-whisper Speech-to-Text engine
├── ptt_overlay.py           # Speech-to-Text floating live dictation UI
├── screen_engine.py         # Screenshot & screen recording engine
├── flash_overlay.py         # Screenshot visual shutter flash overlay
├── actions.py               # Action dispatch & macro execution pipeline
├── config.py                # Configuration management (config.json)
├── tray.py                  # System tray icon & context menu
├── assets/                  # High-contrast Hugeicons vector SVGs
├── requirements.txt         # Python project dependencies
└── MicroAction.spec         # PyInstaller build specification
```

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for details.

---

<p align="center">
  Built with ❤️ for productivity & macro automation.
</p>
