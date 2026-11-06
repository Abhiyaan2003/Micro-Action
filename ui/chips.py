"""Pill-shaped action-type selectors."""
from __future__ import annotations

from PyQt6.QtCore import QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PyQt6.QtWidgets import QPushButton

from ui.glass import paint_glass_surface
from ui.icons import icon_pixmap
from ui.theme import DARK, ThemeTokens, token_color


class ActionChip(QPushButton):
    chosen = pyqtSignal(str)

    def __init__(self, action_type: str, label: str, theme: ThemeTokens = DARK, parent=None):
        super().__init__(label, parent)
        self.action_type = action_type
        self.theme = theme
        self._hover = False
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(30)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent; border: none;")
        self.setAccessibleName(f"{label} action type")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.clicked.connect(lambda: self.chosen.emit(self.action_type))

    def sizeHint(self) -> QSize:
        font = self.font()
        font.setPointSize(9)
        fm = QFontMetrics(font)
        text_w = fm.horizontalAdvance(self.text())
        # Left dot: 11px margin + 6px diameter + 6px gap = 23px. Right padding: 14px.
        width = text_w + 40
        return QSize(max(width, 74), 30)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def set_theme(self, theme: ThemeTokens):
        self.theme = theme
        self.update()

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, a0):
        self._hover = False
        self.update()
        super().leaveEvent(a0)

    def paintEvent(self, a0):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        r = rect.height() / 2.0

        if self.isChecked():
            painter.setPen(QPen(QColor(168, 85, 247, 110), 1.2))
            painter.setBrush(QColor(168, 85, 247, 24))
            painter.drawRoundedRect(rect, r, r)

            # Purple glowing dot
            dot_color = QColor("#A855F7")
            dot_r = 3.0
            dot_x = rect.left() + 11.0
            dot_y = rect.center().y()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(dot_color)
            painter.drawEllipse(QRectF(dot_x - dot_r, dot_y - dot_r, dot_r * 2, dot_r * 2))

            painter.setPen(QColor("#FFFFFF"))
            font = painter.font()
            font.setPointSize(9)
            font.setWeight(QFont.Weight.Medium)
            painter.setFont(font)
            text_rect = QRectF(dot_x + dot_r + 6, rect.top(), rect.width() - (dot_x + dot_r + 6) - 12, rect.height())
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.text())
        else:
            if self._hover:
                painter.setPen(QPen(QColor(255, 255, 255, 25), 1))
                painter.setBrush(QColor(255, 255, 255, 12))
                painter.drawRoundedRect(rect, r, r)

            painter.setPen(QColor(255, 255, 255, 220 if self._hover else 150))
            font = painter.font()
            font.setPointSize(9)
            font.setWeight(QFont.Weight.Normal)
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())

        if self.hasFocus():
            painter.setPen(QPen(QColor("#A855F7"), 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), r, r)

        painter.end()
