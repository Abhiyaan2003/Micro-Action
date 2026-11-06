"""Theme tokens and Windows appearance detection for the glass UI."""
from __future__ import annotations

from dataclasses import dataclass
import re

from PyQt6.QtGui import QColor, QFontDatabase


@dataclass(frozen=True)
class ThemeTokens:
    name: str
    bg: str
    bg_glow: str
    glass: str
    glass_hover: str
    sheen: str
    rim: str
    text: str
    text_dim: str
    inset: str
    shadow: str
    pill: str
    on: str
    off: str
    danger: str
    actions: dict[str, str]


DARK = ThemeTokens(
    name="dark", bg="#0B0C10", bg_glow="rgba(168,85,247,0.03)",
    glass="rgba(255,255,255,0.04)", glass_hover="rgba(255,255,255,0.07)",
    sheen="rgba(255,255,255,0.05)", rim="rgba(255,255,255,0.08)",
    text="#FFFFFF", text_dim="rgba(255,255,255,0.50)",
    inset="#0E1017", shadow="rgba(0,0,0,0.30)",
    pill="rgba(255,255,255,0.05)", on="#10B981", off="#6B7280", danger="#FF5555",
    actions={
        "website": "#FFFFFF", "hotkey": "#C084FC", "launch": "#FFFFFF",
        "script": "#FFFFFF", "ptt": "#FF5C7A", "screenshot": "#FFFFFF",
        "screenrec": "#FFFFFF", "volume": "#FFFFFF", "brightness": "#FFFFFF",
    },
)

LIGHT = ThemeTokens(
    name="light", bg="#EEF1F7", bg_glow="rgba(120,140,255,0.10)",
    glass="rgba(255,255,255,0.70)", glass_hover="rgba(255,255,255,0.95)",
    sheen="rgba(255,255,255,0.45)", rim="rgba(255,255,255,0.95)",
    text="rgba(15,18,30,0.92)", text_dim="rgba(15,18,30,0.68)",
    inset="rgba(15,18,30,0.06)", shadow="rgba(30,40,70,0.18)",
    pill="rgba(255,255,255,0.92)", on="#168B5E", off="#73798A", danger="#C93138",
    actions={
        "website": "#246AB7", "hotkey": "#7546B5", "launch": "#168B5E",
        "script": "#A86600", "ptt": "#C33F62", "screenshot": "#087E91",
        "screenrec": "#C93138", "volume": "#4A5365", "brightness": "#4A5365",
    },
)


def windows_uses_light_theme() -> bool:
    """Read AppsUseLightTheme; safely fall back to the requested dark default."""
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as key:
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return bool(value)
    except (OSError, ImportError):
        return False


def theme_for(appearance: str = "system") -> ThemeTokens:
    if appearance == "light":
        return LIGHT
    if appearance == "dark":
        return DARK
    return LIGHT if windows_uses_light_theme() else DARK


_RGBA_TOKEN = re.compile(r"^rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)$", re.I)


def token_color(value: str) -> QColor:
    """Parse design tokens, including CSS fractional alpha, as a QColor."""
    match = _RGBA_TOKEN.match(value)
    if match:
        red, green, blue = (int(match.group(index)) for index in (1, 2, 3))
        alpha_value = float(match.group(4))
        alpha = round(alpha_value * 255) if alpha_value <= 1 else round(alpha_value)
        return QColor(red, green, blue, max(0, min(255, alpha)))
    return QColor(value)


def stylesheet_tokens(value: str) -> str:
    """Convert fractional token alpha to Qt stylesheet's integer alpha."""
    def convert(match: re.Match[str]) -> str:
        alpha_value = float(match.group(4))
        alpha = round(alpha_value * 255) if alpha_value <= 1 else round(alpha_value)
        return f"rgba({match.group(1)},{match.group(2)},{match.group(3)},{max(0, min(255, alpha))})"
    return re.sub(r"rgba\((\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\)", convert, value, flags=re.I)


def interface_font_family() -> str:
    available = set(QFontDatabase.families())
    for family in ("Segoe UI Variable Text", "Segoe UI Variable", "Segoe UI", "Inter", "Arial"):
        if family in available:
            return family
    return "Arial"


def mono_font_family() -> str:
    available = set(QFontDatabase.families())
    for family in ("Cascadia Mono", "Consolas"):
        if family in available:
            return family
    return "Consolas"
