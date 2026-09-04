import html
from PyQt6.QtWidgets import QLabel, QApplication
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from config import get_resource_path
import os

class OverlaySignals(QObject):
    show_sig = pyqtSignal()
    hide_sig = pyqtSignal()
    message_sig = pyqtSignal(str)
    partial_sig = pyqtSignal(str, str)  # (committed_text, tentative_text)

class PTTOverlay(QLabel):
    """
    Floating hardware utility pill showing PTT speech recording state and live transcription preview.
    Must be instantiated on the main Qt thread.
    """
    def __init__(self):
        super().__init__("🎙️ Listening...")
        self.signals = OverlaySignals()
        self.signals.show_sig.connect(self._show)
        self.signals.hide_sig.connect(self._hide)
        self.signals.message_sig.connect(self._set_text)
        self.signals.partial_sig.connect(self._set_partial)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                background-color: #161922;
                color: #f8fafc;
                border: 1px solid #2d3345;
                border-left: 4px solid #f59e0b;
                border-radius: 8px;
                padding: 10px 24px;
                font-size: 13px;
                font-weight: 700;
                font-family: 'Consolas', monospace;
                letter-spacing: 0.5px;
            }
        """)
        self.adjustSize()
        self._position_bottom_center()

    def _position_bottom_center(self):
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.geometry()
            self.move(
                geom.center().x() - self.width() // 2,
                geom.bottom() - 120
            )

    def set_message(self, text: str):
        self.signals.message_sig.emit(text)

    def set_partial(self, committed: str, tentative: str):
        self.signals.partial_sig.emit(committed, tentative)

    def show_recording(self):
        self.signals.show_sig.emit()

    def hide(self):
        self.signals.hide_sig.emit()

    def _show(self):
        self._position_bottom_center()
        super().show()
        self.raise_()

    def _hide(self):
        super().hide()

    def _set_text(self, text: str):
        self.setText(text)
        self.adjustSize()
        self._position_bottom_center()

    def _set_partial(self, committed: str, tentative: str):
        c_esc = html.escape(committed.strip()) if committed else ""
        t_esc = html.escape(tentative.strip()) if tentative else ""

        if not c_esc and not t_esc:
            self.setText("🎙️ Listening…")
        elif c_esc and not t_esc:
            self.setText(f"🎙️ {c_esc}")
        elif not c_esc and t_esc:
            self.setText(f"🎙️ <span style='color: #94a3b8; font-style: italic;'>{t_esc}</span>")
        else:
            self.setText(f"🎙️ {c_esc} <span style='color: #94a3b8; font-style: italic;'>{t_esc}</span>")

        self.adjustSize()
        self._position_bottom_center()
