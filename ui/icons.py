"""Recolour the project's small SVG line icons at paint time."""
from __future__ import annotations

import os

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtSvg import QSvgRenderer

from config import get_resource_path


ACTION_ICONS = {
    "website": "link", "hotkey": "hotkey", "launch": "launch", "script": "script",
    "ptt": "ptt", "screenshot": "screenshot", "screenrec": "screenrec",
}


def icon_pixmap(name: str, color: str, size: int = 22) -> QPixmap:
    if name in ("numpad", "numpad-off", "check"):
        return _draw_system_icon(name, color, size)
    asset_name = ACTION_ICONS.get(name, name)
    path = get_resource_path(os.path.join("assets", "hugeicons", f"{asset_name}.svg"))
    if not os.path.exists(path):
        return QPixmap()
    try:
        with open(path, "r", encoding="utf-8") as icon_file:
            svg = icon_file.read().replace("currentColor", color)
        renderer = QSvgRenderer(svg.encode("utf-8"))
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter, QRectF(0, 0, size, size))
        painter.end()
        return pixmap
    except (OSError, RuntimeError):
        return QPixmap()


def icon(name: str, color: str, size: int = 18) -> QIcon:
    pixmap = icon_pixmap(name, color, size)
    return QIcon(pixmap) if not pixmap.isNull() else QIcon()


def _draw_system_icon(name: str, color: str, size: int) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), max(1.2, size / 16), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
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
    painter.end()
    return pixmap
