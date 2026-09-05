import os
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
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

    def start(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            print("[Tray] System tray is not available on this platform.")
            return

        if os.path.exists(self.icon_path):
            icon = QIcon(self.icon_path)
        else:
            icon = QIcon()

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
