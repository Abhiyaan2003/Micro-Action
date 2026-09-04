from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject


class FlashSignals(QObject):
    flash_sig = pyqtSignal()


class ScreenFlashOverlay(QWidget):
    """
    Full-screen translucent flash overlay to mimic Windows screenshot visual effect.
    Flashes white across all monitors and fades out smoothly over ~250ms.
    Must be instantiated on the main Qt thread.
    """
    def __init__(self):
        super().__init__()
        self.signals = FlashSignals()
        self.signals.flash_sig.connect(self._do_flash)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setStyleSheet("background-color: white;")

        self.opacity = 0.45
        self.fade_timer = QTimer(self)
        self.fade_timer.setInterval(16)  # ~60 FPS smooth fade
        self.fade_timer.timeout.connect(self._fade_step)

    def trigger_flash(self):
        self.signals.flash_sig.emit()

    def _do_flash(self):
        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.virtualGeometry())
        self.opacity = 0.45
        self.setWindowOpacity(self.opacity)
        super().show()
        self.raise_()
        self.fade_timer.start()

    def _fade_step(self):
        self.opacity -= 0.045
        if self.opacity <= 0.0:
            self.fade_timer.stop()
            self.setWindowOpacity(0.0)
            super().hide()
        else:
            self.setWindowOpacity(self.opacity)
