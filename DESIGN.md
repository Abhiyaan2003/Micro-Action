---
name: Micro Action (Reimagined Neo-Brutalist Cyber-Mechanical Edition)
description: High-contrast, stark-border macropad editor and Whisper-PTT voice studio
colors:
  bg-main: "#eef2f6"
  bg-card: "#ffffff"
  bg-plate: "#ffffff"
  text-primary: "#000000"
  text-muted: "#555555"
  accent-cyan: "#00e5ff"
  border-dark: "#000000"
  
  # Action type electric neon block colors
  type-web: "#00e5ff"        # Electric Cyan
  type-hotkey: "#7b61ff"     # Electric Violet
  type-launch: "#ff2a85"     # Electric Magenta
  type-script: "#00e676"     # Electric Emerald
  type-ptt: "#ff9100"        # Electric Amber / Orange
  type-screenshot: "#ffea00" # Electric Yellow
  type-screenrec: "#ff1744"  # Electric Red
typography:
  display:
    fontFamily: "Impact, Arial Black, sans-serif"
    fontSize: "14px"
    letterSpacing: "2.5px"
  body:
    fontFamily: "Consolas, Courier New, monospace"
    fontSize: "12px"
  label:
    fontFamily: "Consolas, Courier New, monospace"
    fontSize: "10px"
rounded:
  sm: "4px"
  md: "6px"
  lg: "8px"
components:
  keycap-assigned:
    backgroundColor: "{colors.type-web}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.md}"
    border: "2px solid #000000"
    shadow: "border-right: 5px solid #000; border-bottom: 5px solid #000;"
    size: "110px 84px"
  keycap-unassigned:
    backgroundColor: "#ffffff"
    textColor: "{colors.text-muted}"
    rounded: "{rounded.md}"
    border: "2px solid #000000"
    shadow: "border-right: 5px solid #000; border-bottom: 5px solid #000;"
    size: "110px 84px"
  status-badge-active:
    backgroundColor: "#00e676"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.lg}"
    border: "2px solid #000000"
---

# Design System: Micro Action (Reimagined Edition)

## Overview

**Creative North Star: "The Cyber-Mechanical Blueprint"**

Micro Action leverages raw, flat surfaces, ultra-high contrast ink strokes (`2px` / `3px`), vibrant electric color blocks (Electric Cyan `#00e5ff`, Electric Violet `#7b61ff`, Electric Magenta `#ff2a85`, Electric Emerald `#00e676`, Electric Amber `#ff9100`), and tactile solid offset drop shadows.

Every interactive card is bordered in solid black ink (`#000000`), jumping off the screen using flat solid block shadows. When clicked, elements compress down by 3px, representing mechanical key travel by collapsing the offset shadow lines.

### Key Characteristics:
- **Thick Solid Inking**: Every panel, container, button, and input field uses solid black strokes (`2px` or `3px`).
- **Electric Accent Blocks**: Assigned keycaps feature electric neon accent badges corresponding to action types.
- **Flat 3D Block Shadows**: Hard 5px/6px bottom-right outlines with 3D tactile press animation.
- **Monospace Technical Legends**: Clean monospace typography (`Consolas`) with tracked Impact headers.

## Colors

- **Electric Cyan Primary** (#00e5ff): Primary brand accent from the official icon.
- **Web Action** (#00e5ff): Electric Cyan for browser & URL actions.
- **Hotkey Action** (#7b61ff): Electric Violet for keyboard shortcut triggers.
- **Launch Action** (#ff2a85): Electric Magenta for application execution.
- **Script Action** (#00e676): Electric Emerald for batch/shell/automation scripts.
- **PTT Action** (#ff9100): Electric Amber for Whisper Push-to-Talk speech transcription.
- **Screenshot Action** (#ffea00): Electric Yellow for display screen capture.
- **Screen Record Action** (#ff1744): Electric Red for video recording.
- **Raw Canvas** (#eef2f6): Clean mechanical backdrop color.
- **Stark White Plate** (#ffffff): Card base and inner keyplate container background.
- **True Black Ink** (#000000): Text, borders, and offset block shadows.
