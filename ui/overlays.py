"""Shared, click-through notification pill for PTT, capture and NumLock state."""
from __future__ import annotations

import math
import re
import time

from PyQt6.QtCore import QEasingCurve, QParallelAnimationGroup, QPropertyAnimation, QRect, Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from ui.backdrop import enable_acrylic
from ui.icons import icon_pixmap
from ui.theme import DARK, ThemeTokens, theme_for


class OverlaySignals(QObject):
    notice = pyqtSignal(str, str, str, str, int, bool)
    partial = pyqtSignal(str, str)
    state = pyqtSignal(bool)
    dismiss = pyqtSignal()


class Waveform(QWidget):
    def __init__(self, color: str, parent=None):
        super().__init__(parent)
        self.color = QColor(color)
        self.setFixedSize(36, 22)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._started = time.monotonic()

    def start(self):
        self._started = time.monotonic()
        self._timer.start(110)
        self.show()

    def stop(self):
        self._timer.stop()
        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(self.color, 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        tick = time.monotonic() - self._started
        for index in range(5):
            height = 4 + 12 * abs(math.sin(tick * 5.0 + index * 0.85))
            x = 4 + index * 7
            painter.drawLine(x, int((self.height() - height) / 2), x, int((self.height() + height) / 2))
        painter.end()


class OverlayPill(QWidget):
    """One reusable native overlay; all public updates are marshalled by signals."""

    def __init__(self, appearance: str = "system", parent=None):
        super().__init__(parent)
        self.theme: ThemeTokens = theme_for(appearance)
        self.signals = OverlaySignals()
        self.signals.notice.connect(self._show_notice)
        self.signals.partial.connect(self._set_partial)
        self.signals.state.connect(self._show_state)
        self.signals.dismiss.connect(self._hide_overlay)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setMinimumWidth(212)
        self.setMaximumWidth(560)
        self._acrylic_applied = False
        self._generation = 0
        self._fade_group = None
        self._status_kind = "notice"

        from PyQt6.QtWidgets import QHBoxLayout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 12, 20, 12)
        layout.setSpacing(12)
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(24, 24)
        layout.addWidget(self.icon_label, 0, Qt.AlignmentFlag.AlignVCenter)

        self.waveform = Waveform(self.theme.actions["ptt"], self)
        layout.addWidget(self.waveform, 0, Qt.AlignmentFlag.AlignVCenter)
        self.waveform.hide()

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        self.title_label = QLabel()
        self.title_label.setTextFormat(Qt.TextFormat.PlainText)
        self.title_label.setStyleSheet(f"color: {self.theme.text}; font-size: 13px; font-weight: 600; background: transparent;")
        self.detail_label = QLabel()
        self.detail_label.setTextFormat(Qt.TextFormat.RichText)
        self.detail_label.setStyleSheet(f"color: {self.theme.text_dim}; font-size: 11px; font-weight: 400; background: transparent;")
        self.detail_label.setWordWrap(True)
        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.detail_label)
        layout.addLayout(text_layout, 1)

        self._auto_hide = QTimer(self)
        self._auto_hide.setSingleShot(True)
        self._auto_hide.timeout.connect(self._hide_overlay)
        self.setStyleSheet("background: transparent;")
        self.adjustSize()

    def set_message(self, text: str):
        clean = self._clean_text(text)
        icon_name, color = self._icon_for(clean)
        self.signals.notice.emit(clean, "", icon_name, color, 0, icon_name == "ptt")

    def set_partial(self, committed: str, tentative: str):
        self.signals.partial.emit(committed, tentative)

    def show_recording(self):
        if not self.isVisible():
            self.signals.notice.emit("Listening…", "", "ptt", self.theme.actions["ptt"], 0, True)
        else:
            self.signals.notice.emit(self.title_label.text(), self.detail_label.text(), "ptt", self.theme.actions["ptt"], 0, True)

    def show_state(self, macros_active: bool):
        self.signals.state.emit(bool(macros_active))

    def show_saved(self, detail: str = "Changes saved"):
        self.show_toast("Saved", detail, icon_name="check", duration_ms=1400)

    def show_action(self, title: str, detail: str = "", action_type: str = "screenshot", duration_ms: int = 1400):
        self.show_toast(title, detail, icon_name=action_type, color=self.theme.actions.get(action_type, self.theme.text_dim), duration_ms=duration_ms)

    def show_toast(self, title: str, detail: str = "", success: bool = True, color: str | None = None,
                   icon_name: str | None = None, duration_ms: int = 1400):
        kind = icon_name or self._icon_for(title)[0]
        tint = color or (self.theme.on if success else self.theme.danger)
        self.signals.notice.emit(title, detail, kind, tint, duration_ms, False)

    def preview_ptt(self, duration_ms: int = 3000):
        self.signals.notice.emit("Listening…", "PTT preview · microphone not started", "ptt", self.theme.actions["ptt"], duration_ms, True)

    def set_theme(self, theme: ThemeTokens):
        self.theme = theme
        self._acrylic_applied = False
        self.waveform.color = QColor(theme.actions["ptt"])
        self.update()

    @staticmethod
    def _clean_text(text: str) -> str:
        return re.sub(r"^[\W_]+\s*", "", text, flags=re.UNICODE).strip() or text.strip()

    def _icon_for(self, text: str) -> tuple[str, str]:
        lower = text.lower()
        if "screen" in lower or "record" in lower or "capture" in lower:
            action = "screenrec" if "record" in lower or "rec " in lower else "screenshot"
            return action, self.theme.actions[action]
        if "saved" in lower or "success" in lower:
            return "check", self.theme.on
        if "error" in lower or "failed" in lower or "mic error" in lower:
            return "ptt", self.theme.danger
        return "ptt", self.theme.actions["ptt"]

    def _show_notice(self, title: str, detail: str, icon_name: str, color: str, duration_ms: int, recording: bool):
        self._generation += 1
        self._auto_hide.stop()
        self._status_kind = "recording" if recording else "notice"
        self.waveform.setVisible(recording)
        if recording:
            self.waveform.start()
            self.icon_label.hide()
        else:
            self.waveform.stop()
            self.icon_label.setPixmap(icon_pixmap(icon_name, color, 22))
            self.icon_label.show()
        self.title_label.setText(title)
        self.title_label.setStyleSheet(f"color: {self.theme.text}; font-size: 13px; font-weight: 600; background: transparent;")
        self.detail_label.setText(detail)
        self.detail_label.setVisible(bool(detail))
        self.adjustSize()
        self._animate_show()
        if duration_ms > 0:
            self._auto_hide.start(duration_ms)

    def _set_partial(self, committed: str, tentative: str):
        from html import escape
        self._generation += 1
        self._auto_hide.stop()
        self._status_kind = "recording"
        self.waveform.start()
        self.waveform.show()
        self.icon_label.hide()
        self.title_label.setText("Listening…")
        committed = escape(committed.strip())
        tentative = escape(tentative.strip())
        parts = [committed]
        if tentative:
            parts.append(f"<span style='color:{self.theme.text_dim}; font-style:italic'>{tentative}</span>")
        text = " ".join(part for part in parts if part)
        self.detail_label.setText(text)
        self.detail_label.setVisible(bool(text))
        self.adjustSize()
        if not self.isVisible():
            self._animate_show()

    def _show_state(self, active: bool):
        self._generation += 1
        self._auto_hide.stop()
        self._status_kind = "state"
        self.waveform.stop()
        self.icon_label.show()
        if active:
            self.icon_label.setPixmap(icon_pixmap("numpad", self.theme.on, 24))
            title = "Micro Action is on"
            detail = "Your numpad now runs macros"
            color = self.theme.on
        else:
            self.icon_label.setPixmap(icon_pixmap("numpad-off", self.theme.off, 24))
            title = "Micro Action is off"
            detail = "Your numpad types numbers again"
            color = self.theme.off
        self.title_label.setText(title)
        self.title_label.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: 600; background: transparent;")
        self.detail_label.setText(detail)
        self.detail_label.setStyleSheet(f"color: {self.theme.text_dim}; font-size: 12px; font-weight: 400; background: transparent;")
        self.detail_label.show()
        self.adjustSize()
        self._animate_show()
        self._auto_hide.start(2400)

    def _animate_show(self):
        self._position_bottom_center()
        target = self.geometry()
        start = QRect(target.center().x() - int(target.width() * 0.46), target.y() + 12,
                      int(target.width() * 0.92), max(1, int(target.height() * 0.92)))
        self.setGeometry(start)
        self.setWindowOpacity(0.0)
        super().show()
        self.raise_()
        if not self._acrylic_applied:
            enabled = enable_acrylic(int(self.winId()), "#CC1A1D27" if self.theme.name == "dark" else "#CCF3F5FA")
            self._acrylic_applied = enabled
        if self._fade_group:
            self._fade_group.stop()
        self._fade_group = QParallelAnimationGroup(self)
        move = QPropertyAnimation(self, b"geometry", self._fade_group)
        move.setDuration(200)
        move.setStartValue(start)
        move.setEndValue(target)
        move.setEasingCurve(QEasingCurve.Type.OutCubic)
        opacity = QPropertyAnimation(self, b"windowOpacity", self._fade_group)
        opacity.setDuration(200)
        opacity.setStartValue(0.0)
        opacity.setEndValue(1.0)
        opacity.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_group.addAnimation(move)
        self._fade_group.addAnimation(opacity)
        self._fade_group.start()

    def _position_bottom_center(self):
        screen = QApplication.primaryScreen()
        if screen:
            area = screen.availableGeometry()
            self.adjustSize()
            self.move(area.center().x() - self.width() // 2, area.bottom() - self.height() - 32)

    def _hide_overlay(self):
        self._auto_hide.stop()
        self.waveform.stop()
        if not self.isVisible():
            return
        animation = QPropertyAnimation(self, b"windowOpacity", self)
        animation.setDuration(220)
        animation.setStartValue(self.windowOpacity())
        animation.setEndValue(0.0)
        animation.setEasingCurve(QEasingCurve.Type.InCubic)
        animation.finished.connect(super().hide)
        animation.start()
        self._hide_animation = animation

    def hide(self):
        self.signals.dismiss.emit()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(0.5, 0.5, -0.5, -0.5)
        painter.setPen(QPen(QColor(self.theme.rim), 1))
        painter.setBrush(QColor(self.theme.pill))
        painter.drawRoundedRect(rect, 999, 999)
        painter.end()


StateOverlay = OverlayPill
