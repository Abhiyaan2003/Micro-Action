"""Theme tokens and Windows appearance detection for the glass UI."""
from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtGui import QFontDatabase


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
    name="dark", bg="#0E1015", bg_glow="rgba(90,110,255,0.10)",
    glass="rgba(255,255,255,0.06)", glass_hover="rgba(255,255,255,0.10)",
    sheen="rgba(255,255,255,0.08)", rim="rgba(255,255,255,0.14)",
    text="rgba(255,255,255,0.92)", text_dim="rgba(255,255,255,0.50)",
    inset="rgba(0,0,0,0.25)", shadow="rgba(0,0,0,0.25)",
    pill="rgba(26,29,39,0.60)", on="#4ADE9A", off="#8B91A3", danger="#FF5555",
    actions={
        "website": "#5AA9FF", "hotkey": "#B58CFF", "launch": "#4ADE9A",
        "script": "#FFB84D", "ptt": "#FF6B88", "screenshot": "#4FD8E8",
        "screenrec": "#FF5555", "volume": "#C9D1E0", "brightness": "#C9D1E0",
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
