"""Painted, accessible numpad key tiles."""
from __future__ import annotations

import os

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, Qt, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QPushButton

from ui.glass import paint_glass_surface
from ui.icons import icon_pixmap
from ui.theme import DARK, ThemeTokens, mono_font_family


ACTION_LABELS = {
    "website": "Website", "hotkey": "Hotkey", "launch": "Application",
    "script": "Script", "ptt": "Speech to text", "screenshot": "Screenshot",
    "screenrec": "Screen recording",
}


class KeyTile(QPushButton):
    selected = pyqtSignal(str)

    def __init__(self, pos_id: str, number: str, secondary: str, theme: ThemeTokens = DARK, wide: bool = False, parent=None):
        super().__init__(parent)
        self.pos_id = pos_id
        self.number = number
        self.secondary = secondary
        self.theme = theme
        self._glass_cache = QPixmap()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.action: dict | None = None
        self.label = "Empty"
        self.value = ""
        self._hover_progress = 0.0
        self._press_progress = 0.0
        self._active_glow = 0.0
        self._selected = False
        self._macro_active = True
        self._hover_animation = self._animation(b"hoverProgress", 0.0, 1.0, 120, QEasingCurve.Type.OutCubic)
        self._press_animation = self._animation(b"pressProgress", 0.0, 1.0, 90, QEasingCurve.Type.OutQuad)
        self._release_animation = self._animation(b"pressProgress", 1.0, 0.0, 200, QEasingCurve.Type.OutBack)
        self._pulse_animation = self._animation(b"activeGlow", 0.15, 1.0, 700, QEasingCurve.Type.InOutSine)
        self._pulse_animation.setLoopCount(-1)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setColor(QColor(0, 0, 0, 0))
        shadow.setBlurRadius(0)
        shadow.setOffset(0, 8)
        self.setGraphicsEffect(shadow)
        self._shadow = shadow

        self.setFixedSize(196 if wide else 92, 92)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.clicked.connect(lambda: self.selected.emit(self.pos_id))
        self.pressed.connect(self._pressed)
        self.released.connect(self._released)
        self.setAccessibleName(f"Key {number}")
        self.setToolTip(f"Key {number} · {secondary}\nEmpty")

    def _animation(self, property_name: bytes, start, end, duration: int, easing: QEasingCurve.Type):
        animation = QPropertyAnimation(self, property_name, self)
        animation.setDuration(duration)
        animation.setStartValue(start)
        animation.setEndValue(end)
        animation.setEasingCurve(easing)
        return animation

    def get_hover_progress(self):
        return self._hover_progress

    def set_hover_progress(self, value):
        self._hover_progress = float(value)
        self._refresh_surface()

    hoverProgress = pyqtProperty(float, get_hover_progress, set_hover_progress)

    def get_press_progress(self):
        return self._press_progress

    def set_press_progress(self, value):
        self._press_progress = float(value)
        self.update()

    pressProgress = pyqtProperty(float, get_press_progress, set_press_progress)

    def get_active_glow(self):
        return self._active_glow

    def set_active_glow(self, value):
        self._active_glow = float(value)
        self.update()

    activeGlow = pyqtProperty(float, get_active_glow, set_active_glow)

    def set_action(self, action: dict | None):
        self.action = action
        if action:
            action_type = action.get("type", "")
            self.label = (action.get("desc") or ACTION_LABELS.get(action_type, "Action")).strip()
            self.value = self._value_summary(action_type, action.get("value", ""), bool(action.get("desc")))
            name = f"Key {self.number}, {self.label}"
            if self.value:
                name += f", {self.value}"
            self.setAccessibleName(name)
            self.setToolTip(f"Key {self.number} · {self.secondary}\n{self.label}" + (f"\n{self.value}" if self.value else ""))
        else:
            self.label = "Empty"
            self.value = ""
            self.setAccessibleName(f"Key {self.number}, Empty")
            self.setToolTip(f"Key {self.number} · {self.secondary}\nEmpty")
        self._refresh_surface()

    @staticmethod
    def _value_summary(action_type: str, value: str, has_name: bool) -> str:
        if action_type == "website":
            if "|" in value:
                _, value = value.split("|", 1)
            return value.replace("https://", "").replace("http://", "").replace("www.", "")
        if action_type in ("launch", "script"):
            return os.path.basename(value)
        if action_type == "hotkey":
            return value or "Shortcut"
        if action_type == "ptt":
            return "Hold to speak"
        if action_type in ("screenshot", "screenrec"):
            return value.split("|")[0].replace("_", " ").title() or "Full screen"
        return value

    def set_selected(self, selected: bool):
        if self._selected == selected:
            return
        self._selected = selected
        self._refresh_surface()
        self._update_shadow()

    def set_macro_active(self, active: bool):
        self._macro_active = active
        self.update()

    def set_recording(self, recording: bool):
        if recording:
            self._pulse_animation.start()
        else:
            self._pulse_animation.stop()
            self._active_glow = 0.0
        self.update()

    def enterEvent(self, event):
        self._hover_animation.stop()
        self._hover_animation.setStartValue(self._hover_progress)
        self._hover_animation.setEndValue(1.0)
        self._hover_animation.start()
        self._update_shadow()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover_animation.stop()
        self._hover_animation.setStartValue(self._hover_progress)
        self._hover_animation.setEndValue(0.0)
        self._hover_animation.start()
        self._update_shadow()
        super().leaveEvent(event)

    def _pressed(self):
        self._release_animation.stop()
        self._press_animation.start()

    def _released(self):
        self._press_animation.stop()
        self._release_animation.setStartValue(self._press_progress)
        self._release_animation.start()

    def _refresh_surface(self):
        self._glass_cache = QPixmap()
        self.update()
        self._update_shadow()

    def _update_shadow(self):
        active = self._selected or self._hover_progress > 0.05
        if active:
            action_type = self.action.get("type", "") if self.action else ""
            color = QColor(self.theme.actions.get(action_type, "#000000"))
            color.setAlpha(55)
            self._shadow.setColor(color)
            self._shadow.setBlurRadius(24)
        else:
            self._shadow.setBlurRadius(0)
            self._shadow.setColor(QColor(0, 0, 0, 0))

    def set_theme(self, theme: ThemeTokens):
        self.theme = theme
        self._refresh_surface()

    def resizeEvent(self, event):
        self._glass_cache = QPixmap()
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        scale = 1.0 - self._press_progress * 0.03
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(scale, scale)
        painter.translate(-self.width() / 2, -self.height() / 2)
        painter.drawPixmap(0, 0, self._glass_cache) if not self._glass_cache.isNull() else None
        if self._glass_cache.isNull():
            self._paint_surface(painter)

        rect = QRectF(self.rect())
        action_type = self.action.get("type", "") if self.action else ""
        emphasized = self._selected or self._hover_progress > 0.05
        accent = self.theme.actions.get(action_type, self.theme.text_dim) if emphasized else self.theme.text_dim
        if not self._macro_active:
            accent = self.theme.off
        if self._active_glow > 0 and self.action and action_type == "ptt":
            c = QColor(accent)
            c.setAlphaF(min(1.0, 0.4 + self._active_glow * 0.6))
            accent = c.name(QColor.NameFormat.HexArgb)

        top_font = QFont(self.font())
        top_font.setPointSize(9)
        top_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(top_font)
        painter.setPen(QColor(self.theme.text_dim))
        painter.drawText(QRectF(10, 7, rect.width() - 20, 16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.number)

        if self.action and action_type == "hotkey":
            mono = QFont(self.font())
            mono.setFamily(mono_font_family())
            mono.setPointSize(7)
            painter.setFont(mono)
            painter.setPen(QColor(self.theme.actions.get("hotkey", accent)))
            shortcut = self.action.get("value", "").upper().replace("CTRL", "⌃").replace("SHIFT", "⇧").replace("ALT", "⌥").replace("WIN", "⊞")
            painter.drawText(QRectF(28, 6, rect.width() - 36, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, shortcut)

        glyph = icon_pixmap(action_type if self.action else "add", accent, 24)
        if glyph.isNull() and not self.action:
            glyph = self._plus_icon(accent)
        if not glyph.isNull():
            painter.drawPixmap(int(rect.center().x() - glyph.width() / 2), 26, glyph)

        font = QFont(self.font())
        font.setPointSize(9)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        painter.setPen(QColor(self.theme.text if self.action else self.theme.text_dim))
        label = painter.fontMetrics().elidedText(self.label, Qt.TextElideMode.ElideRight, int(rect.width() - 16))
        painter.drawText(QRectF(8, 56, rect.width() - 16, 16), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label)

        small = QFont(self.font())
        small.setPointSize(7)
        painter.setFont(small)
        painter.setPen(QColor(self.theme.text_dim))
        value = painter.fontMetrics().elidedText(self.value, Qt.TextElideMode.ElideMiddle, int(rect.width() - 16))
        painter.drawText(QRectF(8, 72, rect.width() - 16, 14), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, value)

        if self.hasFocus():
            painter.setPen(QPen(QColor(self.theme.actions.get(action_type, self.theme.off)), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 16, 16)
        painter.end()

    def _paint_surface(self, painter):
        dpr = self.devicePixelRatioF()
        self._glass_cache = QPixmap(int(self.width() * dpr), int(self.height() * dpr))
        self._glass_cache.setDevicePixelRatio(dpr)
        self._glass_cache.fill(Qt.GlobalColor.transparent)
        surface_painter = QPainter(self._glass_cache)
        surface_painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._paint_glass(surface_painter)
        surface_painter.end()
        painter.drawPixmap(0, 0, self._glass_cache)

    def _paint_glass(self, painter):
        strength = max(self._hover_progress, 1.0 if self._selected else 0.0)
        accent = self.theme.actions.get(self.action.get("type", "")) if self.action and (self._selected or strength > 0.05) else None
        paint_glass_surface(painter, QRectF(0.5, 0.5, self.width() - 1, self.height() - 1), self.theme, 16, accent, strength)

    def _plus_icon(self, color: str) -> QPixmap:
        from PyQt6.QtGui import QPainter, QPen
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(color), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(12, 5, 12, 19)
        painter.drawLine(5, 12, 19, 12)
        painter.end()
        return pixmap
