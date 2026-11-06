# design.md — Minimal Glass UI for KeySpark (MacroDeck)

A quiet, dark, slightly luminous interface inspired by Apple's Liquid Glass, adapted for a Windows + PyQt6 tray utility. Glass is used only where it earns its place (key tiles and overlays). Everything else is flat, dark and spacious.

Apple has not published exact values, so numbers here are tuned approximations.

---

## 1. Principles

1. **One idea per screen.** The key grid is the hero. Everything else stays out of its way.
2. **Glass only on tiles and overlays.** The window itself is a flat dark surface.
3. **Color is rare.** Neutral by default. An action's color appears only on hover, selection or active state.
4. **Space over decoration.** No borders where spacing does the job. No heavy shadows.
5. **Soft, short motion.** Small, quick, eased. Nothing bounces for long.
6. **No glass on glass.** One translucent layer per surface.
7. **Honest state.** On and off must be obvious without reading.

---

## 2. Color Tokens

### Dark (default)
| Token | Value | Use |
|---|---|---|
| `bg` | `#0E1015` | Window background |
| `bg.glow` | `rgba(90,110,255,0.10)` | Faint radial glow behind the grid (top-left) |
| `glass` | `rgba(255,255,255,0.06)` | Tile fill |
| `glass.hover` | `rgba(255,255,255,0.10)` | Hover / selected fill |
| `sheen` | `rgba(255,255,255,0.08)` | Top-to-bottom gradient on tiles (fades to 0 at 60% height) |
| `rim` | `rgba(255,255,255,0.14)` | 1 px edge |
| `text` | `rgba(255,255,255,0.92)` | Primary text |
| `text.dim` | `rgba(255,255,255,0.50)` | Secondary text, idle icons |
| `inset` | `rgba(0,0,0,0.25)` | Input fill |
| `shadow` | `rgba(0,0,0,0.25)` | Hover shadow |
| `pill` | `rgba(26,29,39,0.60)` | Overlay fill (over blur) |
| `on` | `#4ADE9A` | Macros on |
| `off` | `#8B91A3` | Macros off |
| `danger` | `#FF5555` | Destructive |

### Light
| Token | Value |
|---|---|
| `bg` | `#EEF1F7` |
| `glass` | `rgba(255,255,255,0.70)` |
| `glass.hover` | `rgba(255,255,255,0.95)` |
| `rim` | `rgba(255,255,255,0.95)` |
| `text` | `rgba(15,18,30,0.92)` |
| `text.dim` | `rgba(15,18,30,0.55)` |
| `inset` | `rgba(15,18,30,0.06)` |
| `shadow` | `rgba(30,40,70,0.18)` |
| `pill` | `rgba(255,255,255,0.65)` |

Follow the Windows app theme setting (light/dark). Dark is the default if it cannot be read.

### Action accents
Used only on the icon, hover glow, selected rim and the chip dot.

| Action | Color |
|---|---|
| Web link | `#5AA9FF` |
| Hotkey | `#B58CFF` |
| Launch app | `#4ADE9A` |
| Script | `#FFB84D` |
| Push-to-talk | `#FF6B88` |
| Screenshot | `#4FD8E8` |
| Screen record | `#FF5555` |
| Volume / Brightness | `#C9D1E0` |

---

## 3. Typography

| Role | Font | Size / Weight |
|---|---|---|
| Title | Segoe UI Variable Display | 18 px, 600 |
| Body, labels | Segoe UI Variable Text | 14 px, 400 |
| Tile label | Segoe UI Variable Text | 12 px, 500 |
| Subtext | Segoe UI Variable Text | 10.5–12.5 px, `text.dim` |
| Hotkeys, paths | Cascadia Mono (fallback Consolas) | 10.5 px |

Fallback stack: Segoe UI, Inter, Arial. Sentence case. No all-caps. No Impact or Arial Black.

---

## 4. Shape, Spacing, Elevation

- **Radii:** window 20, tile 16, button 10, chip 999, overlay pill 999.
- **Spacing scale:** 4 / 8 / 12 / 16 / 24 / 32. Window padding 24. Tile gap 12.
- **Tile size:** 92 × 92. The `0` key spans two columns.
- **Rim:** 1 px, brighter at top-left, fading toward bottom-right.
- **Idle tile shadow:** none. **Hover/selected:** blur 24, offset (0, 8), `shadow`.
- **Never:** hard offset shadows, thick black outlines.

---

## 5. Layout

Two columns, 40 px apart, below a header.

```
Header:  KeySpark (title)                      [● NumLock off, macros on]
Left:    Key grid, 3 columns
           7  8  9
           4  5  6
           1  2  3
           0 (wide)  .
         Hint text under grid
Right:   Editor panel (max width 420)
           Key title ("Key 7") + subtitle ("Web link action")
           Action chips (wrap)
           Name field
           Value field (label changes by action type)
           Buttons: Save changes (primary), Preview push-to-talk, Clear key (destructive on hover)
```

Under 760 px wide, stack the columns and center them.

The 11 keys: 7, 8, 9, 4, 5, 6, 1, 2, 3, 0, and `.`.

---

## 6. Components

### 6.1 Key tile
- Neutral glass fill, 1 px rim, inset top highlight, centered 22 px line icon (idle color `text.dim`), label below (ellipsis if long), hotkey badge top-right in mono.
- **Hover:** fill → `glass.hover`, icon → action accent with a soft glow, shadow appears.
- **Selected:** same as hover plus the rim tinted with the accent at about 55%.
- **Press:** scale 0.97 (90 ms). Release returns with a small overshoot.
- **Active** (e.g. push-to-talk recording): slow glow pulse on the icon (1.4 s loop).
- **Empty key:** label "Empty", icon stays neutral.

### 6.2 Action chips
- Pill buttons: idle = text only in `text.dim`; hover = glass fill; selected = `glass.hover` fill + rim + a 6 px dot in the action's color.

### 6.3 Buttons
- **Primary:** `glass.hover` fill, rim, inset highlight.
- **Secondary:** text only, glass fill on hover.
- **Destructive:** text only, turns `danger` on hover. Height 36 px, horizontal padding 16 px.

### 6.4 Inputs
- Fill `inset`, no border, radius 10, padding 10 × 12. Focus shows a 1.5 px bottom line in the action's color.

### 6.5 Status button (header)
- Small pill with a 7 px dot and text.
- **On:** dot `on` with soft glow, text "NumLock off, macros on".
- **Off:** dot `off`, no glow, text "NumLock on, macros off".
- Clicking it toggles the same state as NumLock (in the real app, it only reflects the real NumLock state).

### 6.6 Overlay pill (shared by all overlays)
- Frameless, translucent, always on top, click-through, no taskbar entry.
- Centered horizontally, 32 px above the bottom of the primary screen's work area.
- Pill shape, `pill` fill over a real backdrop blur, 1 px `rim`, shadow blur 30 / offset (0, 10).
- Contents: 20 px icon in a state color, then text. Padding 12 × 20, gap 12.
- **Appear:** fade in + rise 12 px + scale 0.92 → 1.0, 200 ms.
- **Dismiss:** fade out, 220 ms.

Overlay variants:

| Variant | Icon | Text | Duration |
|---|---|---|---|
| Flash (action fired) | action icon in accent | action name | 1.4 s |
| Push-to-talk | mic in `#FF6B88` + 5 animated waveform bars | "Listening…" | while key is held (max 3 s in previews) |
| Saved | check | "Saved" | 1.4 s |

### 6.7 On/off notification (NumLock state change)
Same overlay pill, two lines of text.

| State | Icon | Title | Subtitle |
|---|---|---|---|
| On | 3×3 numpad icon, stroke `on` (`#4ADE9A`) | **KeySpark is on** (600) | Your numpad now runs macros (`text.dim`, 12 px) |
| Off | same icon with a diagonal slash, stroke `off` (`#8B91A3`) | **KeySpark is off** (600) | Your numpad types numbers again (`text.dim`, 12 px) |

- Shows for 2.4 s.
- Fires on every NumLock change, not on app start. Optionally a single quiet "on" notification at launch.
- A newer overlay replaces an older one immediately (no stacking).
- The main window, if open, mirrors the state: status dot changes and the tile grid fades to about 40% opacity and desaturates while off.
- No sound by default (optional setting).

### 6.8 Tray
- Native Windows menu. Tray icon has an on variant (colored) and an off variant (monochrome).

---

## 7. Motion

| Interaction | Time | Easing |
|---|---|---|
| Hover | 120 ms | OutCubic |
| Press | 90 ms | OutQuad |
| Release | 200 ms | OutBack (small overshoot) |
| Overlay in | 200 ms | OutCubic |
| Overlay out | 220 ms | InCubic |
| Grid fade (on/off) | 250 ms | OutCubic |

Respect the Windows "Show animations" setting. When off, use instant state changes.

---

## 8. PyQt6 Implementation Notes

**Limits.** Qt has no `backdrop-filter` and cannot do Liquid Glass refraction. The result is frosted glass with careful lighting.

1. **Main window:** frameless, `WA_TranslucentBackground`, rounded rect painted in `paintEvent` with the flat `bg` plus a faint radial glow. No blur needed.
2. **Tile glass:** painted with `QPainter` (fill + vertical sheen gradient + diagonal gradient rim + 1 px top highlight). Cache the static background in a `QPixmap`.
3. **Overlay blur:** Windows 11 uses `DwmSetWindowAttribute` with `DWMWA_SYSTEMBACKDROP_TYPE` (Acrylic = 3). Windows 10 fallback uses `SetWindowCompositionAttribute` with `ACCENT_ENABLE_ACRYLICBLURBEHIND`. Round the overlay window with `DWMWA_WINDOW_CORNER_PREFERENCE` or a mask.
4. **Fallback:** if transparency is disabled or the call fails, paint a solid `#1A1D27` (dark) or `#F3F5FA` (light) pill with the same rim and shadow.
5. **Shadows:** `QGraphicsDropShadowEffect` only on the hovered or selected tile.
6. **Animation:** `QPropertyAnimation` / `QVariantAnimation`. Expose `hoverProgress` and `pressScale` as Qt properties on the tile.
7. **Icons:** draw with `QPainterPath` from SVG path data (stroke 1.7 px, round caps and joins), or ship small SVGs rendered via `QSvgRenderer`. Recolor by painting with the current color.
8. **High DPI:** enable Qt high-DPI scaling; test at 100%, 125% and 150%.
9. **Threading:** overlays are triggered from the keyboard hook thread, so marshal to the UI thread with signals. Never create widgets off-thread.

Suggested structure:

```
ui/
  theme.py       # tokens, light/dark detection, fonts
  glass.py       # GlassWidget: paintEvent, rim, sheen, shadow
  backdrop.py    # DWM / Acrylic helpers (ctypes), solid fallback
  icons.py       # icon paths and renderer
  tiles.py       # KeyTile with hover/press/active animations
  chips.py       # ActionChip, ChipGroup
  overlays.py    # OverlayPill base, FlashOverlay, PttOverlay, StateOverlay
  main_window.py # header, grid, editor panel
```

---

## 9. Accessibility

- Text contrast of at least 4.5:1 against the worst-case background.
- Never rely on color alone: every tile has an icon and label; on/off notification has different icon shape (slash) and wording.
- Keyboard navigation in the window: tab order = grid, chips, fields, buttons; visible 2 px focus ring in the action color.
- Respect Windows transparency and animation settings.
- Provide an accessible name for every tile ("Key 7, Web link, GitHub").

---

## 10. Do / Don't

**Do:** keep it dark, calm and spacious; let one accent speak at a time; reuse one overlay for every notification.
**Don't:** use thick outlines, hard offset shadows, Impact, color-filled idle tiles, glass inside glass, or heavy blur on the main window.

---

## 11. Acceptance Checklist

- [ ] Main window shows 11 tiles in the layout above, neutral at idle.
- [ ] Hover and selection show the action accent on the icon, with glow.
- [ ] Editor panel updates live when a tile or chip is selected.
- [ ] Toggling NumLock shows the correct on/off overlay in under 150 ms.
- [ ] PTT overlay shows animated bars while the key is held.
- [ ] Overlays never steal focus or block clicks.
- [ ] Works on Windows 10 and 11, light and dark, 100–150% scaling.
- [ ] Solid fallback appears when transparency is unavailable.
