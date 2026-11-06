"""Small cached QPainter surface primitives for the glass controls."""
from __future__ import annotations

from PyQt6.QtCore import QLineF, QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPixmap, QPen
from PyQt6.QtWidgets import QWidget

from ui.theme import DARK, ThemeTokens, token_color


def _with_alpha(value: str, factor: float) -> QColor:
    color = token_color(value)
    color.setAlphaF(max(0.0, min(1.0, color.alphaF() * factor)))
    return color


def paint_glass_surface(
    painter: QPainter,
    rect: QRectF,
    theme: ThemeTokens,
    radius: float,
    accent: str | None = None,
    strength: float = 0.0,
) -> None:
    """Paint a frosted fill, a short sheen and a restrained diagonal rim."""
    painter.save()
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    painter.setClipPath(path)

    fill = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    base = token_color(theme.glass)
    hover = token_color(theme.glass_hover)
    current = QColor.fromRgbF(
        base.redF() * (1 - strength) + hover.redF() * strength,
        base.greenF() * (1 - strength) + hover.greenF() * strength,
        base.blueF() * (1 - strength) + hover.blueF() * strength,
        base.alphaF() * (1 - strength) + hover.alphaF() * strength,
    )
    fill.setColorAt(0.0, current)
    fill.setColorAt(1.0, _with_alpha(theme.glass, 0.75 + strength * 0.25))
    painter.fillPath(path, fill)

    sheen = QLinearGradient(
        rect.topLeft(), QPointF(rect.left(), rect.top() + rect.height() * 0.7)
    )
    sheen.setColorAt(0.0, _with_alpha(theme.sheen, 1.0 + strength * 0.2))
    sheen.setColorAt(0.6, _with_alpha(theme.sheen, 0.0))
    painter.fillPath(path, sheen)

    rim = QLinearGradient(rect.topLeft(), rect.bottomRight())
    rim.setColorAt(0.0, token_color(theme.rim))
    rim.setColorAt(0.48, _with_alpha(theme.rim, 0.35))
    rim.setColorAt(1.0, _with_alpha(theme.rim, 0.16))
    if accent:
        rim.setColorAt(0.0, _with_alpha(accent, 0.55))
        rim.setColorAt(0.48, _with_alpha(theme.rim, 0.30))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QBrush(rim), 1.0))
    painter.drawPath(path)

    top_line = QLinearGradient(rect.topLeft(), rect.topRight())
    top_line.setColorAt(0, _with_alpha(theme.rim, 0.75))
    top_line.setColorAt(1, _with_alpha(theme.rim, 0.12))
    painter.setPen(QPen(QBrush(top_line), 1.0))
    painter.drawLine(QLineF(
        QPointF(rect.left() + radius, rect.top() + 1),
        QPointF(rect.right() - radius, rect.top() + 1),
    ))
    painter.restore()


class GlassWidget(QWidget):
    """Base surface with an invalidated-on-resize pixmap cache."""

    def __init__(self, parent=None, theme: ThemeTokens = DARK):
        super().__init__(parent)
        self.theme = theme
        self._glass_cache = QPixmap()
        self._glass_radius = 16.0
        self._glass_strength = 0.0
        self._glass_accent = None
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def set_glass_state(self, strength: float, accent: str | None = None):
        if strength == self._glass_strength and accent == self._glass_accent:
            return
        self._glass_strength = strength
        self._glass_accent = accent
        self._glass_cache = QPixmap()
        self.update()

    def set_theme(self, theme: ThemeTokens):
        self.theme = theme
        self._glass_cache = QPixmap()
        self.update()

    def resizeEvent(self, a0):
        self._glass_cache = QPixmap()
        super().resizeEvent(a0)

    def paintEvent(self, a0):
        dpr = self.devicePixelRatioF()
        cache_size = (int(self.width() * dpr), int(self.height() * dpr))
        if self._glass_cache.isNull() or (self._glass_cache.width(), self._glass_cache.height()) != cache_size:
            cache = QPixmap(*cache_size)
            cache.setDevicePixelRatio(dpr)
            cache.fill(Qt.GlobalColor.transparent)
            painter = QPainter(cache)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = QRectF(0.5, 0.5, max(0, self.width() - 1), max(0, self.height() - 1))
            paint_glass_surface(painter, rect, self.theme, self._glass_radius, self._glass_accent, self._glass_strength)
            painter.end()
            self._glass_cache = cache
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.drawPixmap(0, 0, self._glass_cache)
