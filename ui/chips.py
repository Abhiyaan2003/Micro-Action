"""Pill-shaped action-type selectors."""
from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QPushButton

from ui.glass import paint_glass_surface
from ui.icons import icon_pixmap
from ui.theme import DARK, ThemeTokens


class ActionChip(QPushButton):
    chosen = pyqtSignal(str)

    def __init__(self, action_type: str, label: str, theme: ThemeTokens = DARK, parent=None):
        super().__init__(label, parent)
        self.action_type = action_type
        self.theme = theme
        self._hover = False
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(36)
        self.setAccessibleName(f"{label} action type")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.clicked.connect(lambda: self.chosen.emit(self.action_type))

    def set_theme(self, theme: ThemeTokens):
        self.theme = theme
        self.update()

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        if self.isChecked() or self._hover:
            strength = 1.0 if self.isChecked() else 0.45
            accent = self.theme.actions.get(self.action_type) if self.isChecked() else None
            paint_glass_surface(painter, rect, self.theme, rect.height() / 2, accent, strength)

        icon_color = self.theme.actions.get(self.action_type, self.theme.text_dim) if self.isChecked() else self.theme.text_dim
        glyph = icon_pixmap(self.action_type, icon_color, 16)
        x = rect.left() + 11
        y = rect.center().y() - 8
        if not glyph.isNull():
            painter.drawPixmap(int(x), int(y), glyph)

        painter.setPen(QColor(self.theme.text if self.isChecked() else self.theme.text_dim))
        font = painter.font()
        font.setPointSize(9)
        font.setWeight(QFont.Weight.DemiBold if self.isChecked() else QFont.Weight.Normal)
        painter.setFont(font)
        painter.drawText(QRectF(x + 22, rect.top(), rect.width() - 38, rect.height()), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.text())

        if self.isChecked():
            dot_color = self.theme.actions.get(self.action_type, self.theme.on)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(dot_color))
            painter.drawEllipse(QRectF(rect.right() - 15, rect.center().y() - 3, 6, 6))
        if self.hasFocus():
            painter.setPen(QPen(QColor(self.theme.actions.get(self.action_type, self.theme.off)), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), rect.height() / 2, rect.height() / 2)
        painter.end()
