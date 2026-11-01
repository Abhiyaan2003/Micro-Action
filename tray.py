import os
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction, QPixmap, QColor, QImage
from PyQt6.QtCore import QObject


class SystemTrayApp(QObject):
    """
    Manages the background system tray icon using PyQt6 native QSystemTrayIcon.
    Runs on the Qt event loop with zero background threading issues.
    """
    def __init__(self, icon_path: str, on_show_gui, on_exit):
        super().__init__()
        self.icon_path = icon_path
        self.on_show_gui = on_show_gui
        self.on_exit = on_exit
        self.tray_icon = None
        self.menu = None
        self._base_icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()

    def start(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            print("[Tray] System tray is not available on this platform.")
            return

        icon = self._base_icon

        self.menu = QMenu()
        show_action = QAction("Configure...", self.menu)
        show_action.triggered.connect(self._show_gui_action)
        self.menu.addAction(show_action)

        self.menu.addSeparator()

        exit_action = QAction("Exit", self.menu)
        exit_action.triggered.connect(self._exit_action)
        self.menu.addAction(exit_action)

        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip("Micro Action")
        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.activated.connect(self._on_activated)
        self.tray_icon.show()
        print("[Tray] Native QSystemTrayIcon initialized.")

    def set_macros_active(self, active: bool):
        if not self.tray_icon:
            return
        if active:
            icon = self._base_icon
        elif not self._base_icon.isNull():
            source = self._base_icon.pixmap(32, 32)
            original = source.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
            image = QImage(original.size(), QImage.Format.Format_RGBA8888)
            image.fill(QColor(0, 0, 0, 0))
            for y in range(original.height()):
                for x in range(original.width()):
                    pixel = original.pixelColor(x, y)
                    gray = round(pixel.red() * 0.299 + pixel.green() * 0.587 + pixel.blue() * 0.114)
                    image.setPixelColor(x, y, QColor(gray, gray, gray, pixel.alpha()))
            icon = QIcon(QPixmap.fromImage(image))
        else:
            icon = self._base_icon
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("Micro Action · macros on" if active else "Micro Action · macros off")

    def _on_activated(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick
        ):
            self._show_gui_action()

    def _show_gui_action(self):
        if self.on_show_gui:
            self.on_show_gui()

    def _exit_action(self):
        if self.tray_icon:
            self.tray_icon.hide()
        if self.on_exit:
            self.on_exit()
