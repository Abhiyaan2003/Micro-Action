"""Best-effort Windows Acrylic for floating overlays, with a Qt fallback."""
from __future__ import annotations

import ctypes
import sys


class _AccentPolicy(ctypes.Structure):
    _fields_ = [
        ("AccentState", ctypes.c_int),
        ("AccentFlags", ctypes.c_int),
        ("GradientColor", ctypes.c_uint),
        ("AnimationId", ctypes.c_int),
    ]


class _CompositionAttributeData(ctypes.Structure):
    _fields_ = [
        ("Attribute", ctypes.c_int),
        ("Data", ctypes.c_void_p),
        ("SizeOfData", ctypes.c_size_t),
    ]


def enable_acrylic(hwnd: int, fallback_color: str = "#CC1A1D27") -> bool:
    """Try Windows 11 system backdrop, then the Windows 10 acrylic accent API."""
    if sys.platform != "win32" or not hwnd:
        return False
    try:
        dwm = ctypes.windll.dwmapi
        dwm.DwmSetWindowAttribute.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint]
        dwm.DwmSetWindowAttribute.restype = ctypes.c_long
        backdrop = ctypes.c_int(3)  # DWMSBT_TRANSIENTWINDOW (Acrylic)
        result = dwm.DwmSetWindowAttribute(
            ctypes.c_void_p(hwnd), 38, ctypes.byref(backdrop), ctypes.sizeof(backdrop)
        )
        corner = ctypes.c_int(2)  # DWMWCP_ROUND
        dwm.DwmSetWindowAttribute(
            ctypes.c_void_p(hwnd), 33, ctypes.byref(corner), ctypes.sizeof(corner)
        )
        if result == 0:
            return True
    except (AttributeError, OSError, TypeError):
        pass

    try:
        # WCA_ACCENT_POLICY / ACCENT_ENABLE_ACRYLICBLURBEHIND.
        rgb = fallback_color.lstrip("#")
        if len(rgb) == 8:
            alpha, red, green, blue = (int(rgb[i:i + 2], 16) for i in (0, 2, 4, 6))
        else:
            alpha, red, green, blue = 0xCC, 0x1A, 0x1D, 0x27
        color_abgr = (alpha << 24) | (blue << 16) | (green << 8) | red
        policy = _AccentPolicy(4, 2, color_abgr, 0)
        data = _CompositionAttributeData(19, ctypes.cast(ctypes.byref(policy), ctypes.c_void_p), ctypes.sizeof(policy))
        user32 = ctypes.windll.user32
        user32.SetWindowCompositionAttribute.argtypes = [ctypes.c_void_p, ctypes.POINTER(_CompositionAttributeData)]
        user32.SetWindowCompositionAttribute.restype = ctypes.c_bool
        return bool(user32.SetWindowCompositionAttribute(ctypes.c_void_p(hwnd), ctypes.byref(data)))
    except (AttributeError, OSError, TypeError):
        return False
