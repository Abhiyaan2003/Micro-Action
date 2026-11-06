"""Recolour the project's small SVG line icons at paint time."""
from __future__ import annotations

import os

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtSvg import QSvgRenderer

from config import get_resource_path
from ui.theme import stylesheet_tokens, token_color


import math

ACTION_ICONS = {
    "website": "link", "hotkey": "hotkey", "launch": "launch", "script": "script",
    "ptt": "ptt", "screenshot": "screenshot", "screenrec": "screenrec",
    "volume": "volume", "brightness": "brightness",
}

SYSTEM_ICONS = {
    "numpad", "numpad-off", "check", "hotkey", "vscode", "grid", "deploy",
    "screenshot", "capture", "screenrec", "record", "volume", "volume-up",
    "volume-down", "brightness", "lock", "link", "ptt", "mic",
}


def icon_pixmap(name: str, color: str, size: int = 22) -> QPixmap:
    # First check if explicit system renderer is preferred
    if name in ("numpad", "numpad-off", "check", "vscode", "grid"):
        return _draw_system_icon(name, color, size)

    c = token_color(color)
    hex_color = f"#{c.red():02x}{c.green():02x}{c.blue():02x}"
    opacity = f"{c.alpha() / 255.0:.3f}"

    asset_name = ACTION_ICONS.get(name, name)
    path = get_resource_path(os.path.join("assets", "hugeicons", f"{asset_name}.svg"))
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as icon_file:
                svg = icon_file.read().replace("currentColor", hex_color)
            if c.alpha() < 255:
                svg = svg.replace("<svg ", f'<svg stroke-opacity="{opacity}" fill-opacity="{opacity}" ', 1)
            renderer = QSvgRenderer(svg.encode("utf-8"))
            if renderer.isValid():
                pixmap = QPixmap(size, size)
                pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(pixmap)
                renderer.render(painter, QRectF(0, 0, size, size))
                painter.end()
                if not pixmap.isNull():
                    return pixmap
        except (OSError, RuntimeError):
            pass

    return _draw_system_icon(name, color, size)


def icon(name: str, color: str, size: int = 18) -> QIcon:
    pixmap = icon_pixmap(name, color, size)
    return QIcon(pixmap) if not pixmap.isNull() else QIcon()


def _draw_system_icon(name: str, color: str, size: int) -> QPixmap:
    from PyQt6.QtCore import QPointF
    from PyQt6.QtGui import QPainterPath

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    stroke = max(1.5, size / 15)
    pen = QPen(token_color(color), stroke, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    if name in ("numpad", "numpad-off"):
        margin = size * 0.16
        gap = size * 0.12
        cell = (size - margin * 2 - gap * 2) / 3
        for row in range(3):
            for col in range(3):
                x = margin + col * (cell + gap)
                y = margin + row * (cell + gap)
                painter.drawRoundedRect(QRectF(x, y, cell, cell), cell * 0.2, cell * 0.2)
        if name == "numpad-off":
            painter.drawLine(int(size * 0.15), int(size * 0.85), int(size * 0.85), int(size * 0.15))
    elif name == "check":
        painter.drawLine(int(size * 0.18), int(size * 0.52), int(size * 0.43), int(size * 0.76))
        painter.drawLine(int(size * 0.43), int(size * 0.76), int(size * 0.83), int(size * 0.25))
    elif name == "hotkey":
        # ⌘ Command cloverleaf symbol
        loop_r = size * 0.13
        c1 = size * 0.35
        c2 = size * 0.65
        painter.drawLine(QPointF(c1, c1 - loop_r), QPointF(c1, c2 + loop_r))
        painter.drawLine(QPointF(c2, c1 - loop_r), QPointF(c2, c2 + loop_r))
        painter.drawLine(QPointF(c1 - loop_r, c1), QPointF(c2 + loop_r, c1))
        painter.drawLine(QPointF(c1 - loop_r, c2), QPointF(c2 + loop_r, c2))
        painter.drawArc(QRectF(c1 - 2 * loop_r, c1 - 2 * loop_r, 2 * loop_r, 2 * loop_r), 0, 360 * 16)
        painter.drawArc(QRectF(c2, c1 - 2 * loop_r, 2 * loop_r, 2 * loop_r), 0, 360 * 16)
        painter.drawArc(QRectF(c2, c2, 2 * loop_r, 2 * loop_r), 0, 360 * 16)
        painter.drawArc(QRectF(c1 - 2 * loop_r, c2, 2 * loop_r, 2 * loop_r), 0, 360 * 16)
    elif name in ("vscode", "grid"):
        # 4-square grid icon
        sq = size * 0.26
        gap = size * 0.12
        x1 = (size - (sq * 2 + gap)) / 2
        y1 = x1
        x2 = x1 + sq + gap
        y2 = y1 + sq + gap
        r = sq * 0.25
        painter.drawRoundedRect(QRectF(x1, y1, sq, sq), r, r)
        painter.drawRoundedRect(QRectF(x2, y1, sq, sq), r, r)
        painter.drawRoundedRect(QRectF(x1, y2, sq, sq), r, r)
        painter.drawRoundedRect(QRectF(x2, y2, sq, sq), r, r)
    elif name in ("deploy", "script", "terminal"):
        # >_ Deploy terminal prompt
        painter.drawLine(QPointF(size * 0.22, size * 0.32), QPointF(size * 0.44, size * 0.48))
        painter.drawLine(QPointF(size * 0.44, size * 0.48), QPointF(size * 0.22, size * 0.64))
        painter.drawLine(QPointF(size * 0.52, size * 0.64), QPointF(size * 0.78, size * 0.64))
    elif name in ("screenshot", "capture"):
        # Viewfinder / crop frame
        m = size * 0.22
        w = size * 0.56
        c = size * 0.18
        painter.drawLine(QPointF(m, m + c), QPointF(m, m))
        painter.drawLine(QPointF(m, m), QPointF(m + c, m))
        painter.drawLine(QPointF(m + w - c, m), QPointF(m + w, m))
        painter.drawLine(QPointF(m + w, m), QPointF(m + w, m + c))
        painter.drawLine(QPointF(m + w, m + w - c), QPointF(m + w, m + w))
        painter.drawLine(QPointF(m + w, m + w), QPointF(m + w - c, m + w))
        painter.drawLine(QPointF(m + c, m + w), QPointF(m, m + w))
        painter.drawLine(QPointF(m, m + w), QPointF(m, m + w - c))
    elif name in ("screenrec", "record"):
        # Outer circle + concentric inner circle
        cx, cy = size / 2, size / 2
        painter.drawEllipse(QPointF(cx, cy), size * 0.36, size * 0.36)
        painter.drawEllipse(QPointF(cx, cy), size * 0.18, size * 0.18)
    elif name in ("volume", "volume-up", "volume-down"):
        path = QPainterPath()
        path.moveTo(size * 0.18, size * 0.40)
        path.lineTo(size * 0.32, size * 0.40)
        path.lineTo(size * 0.48, size * 0.24)
        path.lineTo(size * 0.48, size * 0.76)
        path.lineTo(size * 0.32, size * 0.60)
        path.lineTo(size * 0.18, size * 0.60)
        path.closeSubpath()
        painter.drawPath(path)
        # Sound wave arc 1
        painter.drawArc(QRectF(size * 0.48, size * 0.36, size * 0.18, size * 0.28), -45 * 16, 90 * 16)
        if name != "volume-down":
            # Sound wave arc 2
            painter.drawArc(QRectF(size * 0.56, size * 0.26, size * 0.28, size * 0.48), -45 * 16, 90 * 16)
    elif name == "brightness":
        cx, cy = size / 2, size / 2
        r = size * 0.18
        painter.drawEllipse(QPointF(cx, cy), r, r)
        ray_in = size * 0.28
        ray_out = size * 0.42
        for i in range(8):
            ang = i * (math.pi / 4)
            x1 = cx + math.cos(ang) * ray_in
            y1 = cy + math.sin(ang) * ray_in
            x2 = cx + math.cos(ang) * ray_out
            y2 = cy + math.sin(ang) * ray_out
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
    elif name == "lock":
        # Padlock shackle + body
        bw = size * 0.48
        bh = size * 0.38
        bx = (size - bw) / 2
        by = size * 0.48
        painter.drawRoundedRect(QRectF(bx, by, bw, bh), size * 0.08, size * 0.08)
        sw = size * 0.30
        sh = size * 0.28
        sx = (size - sw) / 2
        sy = by - sh + size * 0.04
        painter.drawArc(QRectF(sx, sy, sw, sh * 2), 0, 180 * 16)
    elif name in ("ptt", "mic"):
        # Microphone outline
        mw = size * 0.28
        mh = size * 0.42
        mx = (size - mw) / 2
        my = size * 0.15
        painter.drawRoundedRect(QRectF(mx, my, mw, mh), mw / 2, mw / 2)
        cw = size * 0.46
        ch = size * 0.36
        cx = (size - cw) / 2
        cy = my + mh - ch * 0.75
        painter.drawArc(QRectF(cx, cy, cw, ch), -180 * 16, 180 * 16)
        painter.drawLine(QPointF(size / 2, cy + ch / 2), QPointF(size / 2, size * 0.85))
    elif name in ("link", "website"):
        # Interlocking chain link
        w = size * 0.38
        h = size * 0.26
        r = h / 2.0
        painter.drawRoundedRect(QRectF(size * 0.18, size * 0.37, w, h), r, r)
        painter.drawRoundedRect(QRectF(size * 0.44, size * 0.37, w, h), r, r)
    elif name in ("launch", "app", "application"):
        # Application window with title bar
        m = size * 0.20
        w = size * 0.60
        h = size * 0.55
        painter.drawRoundedRect(QRectF(m, m, w, h), size * 0.08, size * 0.08)
        painter.drawLine(QPointF(m, m + h * 0.32), QPointF(m + w, m + h * 0.32))
    else:
        # Generic link / fallback
        m = size * 0.25
        w = size * 0.50
        painter.drawRoundedRect(QRectF(m, m, w, w), size * 0.12, size * 0.12)

    painter.end()
    return pixmap
