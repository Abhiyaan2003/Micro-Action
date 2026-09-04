import sys
import os

# Suppress Qt DPI awareness error on non-admin processes.
# Must be set before any Qt import.
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "0")
os.environ.setdefault("QT_SCALE_FACTOR", "1")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import pyqtSignal, QTimer

from config import Config, get_resource_path
from actions import ActionEngine
from hook import KeyboardHook
from gui import NumpadEditor
from tray import SystemTrayApp

class MainWindow(NumpadEditor):
    """
    Subclass of NumpadEditor to orchestrate thread-safe GUI signals,
    window close events (minimize to tray), and clean application exits.
    """
    show_signal = pyqtSignal()
    exit_signal = pyqtSignal()

    def __init__(self, config, hook, ptt=None, overlay=None, screen_engine=None):
        super().__init__(config, ptt)
        self.hook = hook
        self.ptt = ptt
        self.overlay = overlay
        self.screen_engine = screen_engine

        # Connect thread-safe tray signals
        self.show_signal.connect(self.show_and_raise)
        self.exit_signal.connect(self.app_exit)

    def show_and_raise(self):
        self.show()
        self.activateWindow()
        self.raise_()

    def closeEvent(self, event):
        """
        Intercept close window event to hide window instead of exiting.
        Runs in background via system tray.
        """
        event.ignore()
        self.hide()

    def app_exit(self):
        """
        Fully shut down the application and release hooks.
        """
        print("[App] Shutting down...")
        self.hook.uninstall()
        if self.ptt:
            self.ptt.stop()
        if self.screen_engine:
            self.screen_engine.force_stop()
        if self.overlay:
            self.overlay.close()
        QApplication.instance().quit()


# Global reference to prevent garbage collection of the mutex handle
_instance_mutex = None

def enable_autostart():
    import sys
    import winreg
    try:
        # Get the path of the current running script/exe
        if getattr(sys, 'frozen', False):
            # Running as compiled exe
            exe_path = sys.executable
        else:
            # Running as script, construct the absolute path to main.py
            script_path = os.path.abspath(sys.argv[0])
            # Use pythonw.exe if running under python.exe to hide the terminal window on startup
            python_exe = sys.executable.replace("python.exe", "pythonw.exe")
            exe_path = f'"{python_exe}" "{script_path}"'

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, "MicroAction", 0, winreg.REG_SZ, exe_path)
        winreg.CloseKey(key)
        print(f"[Startup] Autostart registered in registry: {exe_path}")
    except Exception as e:
        print(f"[Startup] Failed to register autostart: {e}")

def main():
    global _instance_mutex
    
    # Enforce system-wide single instance on Windows using a Named Mutex
    import ctypes
    MUTEX_NAME = "Local\\MicroActionNumpadMacroPadMutex"
    kernel32 = ctypes.windll.kernel32
    _instance_mutex = kernel32.CreateMutexW(None, True, MUTEX_NAME)
    if kernel32.GetLastError() == 183: # ERROR_ALREADY_EXISTS
        print("[App] Another instance of Micro Action is already running. Exiting.")
        # If possible, alert the user or just exit silently to prevent multiple hooks
        sys.exit(0)

    # Configure autostart
    enable_autostart()

    # Set AppUserModelID so Windows taskbar treats it as a distinct application and applies the custom icon properly.
    try:
        import ctypes
        myappid = "Google.MicroAction.NumpadMacro.1.0"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception as e:
        print(f"[App] Failed to set AppUserModelID: {e}")

    # Force single instance check or just run normally
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Set application-wide icon
    from PyQt6.QtGui import QIcon
    icon_path = get_resource_path("app_icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Initialize configuration
    config = Config()

    # Initialize PTT Overlay and Engine (created on Qt main thread)
    from ptt_overlay import PTTOverlay
    from ptt_engine import PTTEngine
    overlay = PTTOverlay()
    ptt_engine = PTTEngine(config=config, overlay=overlay)

    # Initialize Action Dispatcher
    action_engine = ActionEngine()
    action_engine.set_ptt(ptt_engine, overlay)

    # Initialize Screen Capture Engine & Flash Overlay (created on Qt main thread)
    from flash_overlay import ScreenFlashOverlay
    from screen_engine import ScreenEngine
    flash_overlay = ScreenFlashOverlay()
    screen_engine = ScreenEngine(config=config, overlay=overlay, flash_overlay=flash_overlay)
    action_engine.set_screen_engine(screen_engine)

    # Initialize Keyboard Hook (installed later on Qt main thread)
    hook = KeyboardHook(config, action_engine, ptt_engine)

    # Instantiate the main coordinator window
    main_window = MainWindow(config, hook, ptt_engine, overlay, screen_engine)
    hook.gui_notifier = main_window.trigger_physical_key_press

    # Define tray icon path
    tray_icon_path = get_resource_path(os.path.join("assets", "icon.png"))
    if not os.path.exists(tray_icon_path) and os.path.exists(icon_path):
        tray_icon_path = icon_path

    # Initialize Background Tray helper
    tray = SystemTrayApp(
        icon_path=tray_icon_path,
        on_show_gui=lambda: main_window.show_signal.emit(),
        on_exit=lambda: main_window.exit_signal.emit()
    )
    tray.start()

    # Show GUI on startup
    main_window.show()

    # Install keyboard hook on the Qt main thread AFTER exec() starts.
    # WH_KEYBOARD_LL requires its installing thread to have a running message
    # pump. Qt's event loop serves as that pump — no separate thread needed.
    QTimer.singleShot(0, hook.install)

    # Run Qt main loop
    code = app.exec()
    sys.exit(code)


if __name__ == "__main__":
    main()
