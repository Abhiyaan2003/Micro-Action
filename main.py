import sys
import os
import ctypes
import ctypes.wintypes

# In PyInstaller frozen bundle, ensure DLL search directory is correctly registered
# before any PyQt6 or C-extension imports.
if hasattr(sys, "_MEIPASS"):
    base_dir = getattr(sys, "_MEIPASS", "")
    qt_bin = os.path.join(base_dir, "PyQt6", "Qt6", "bin")
    if os.path.isdir(qt_bin):
        try:
            os.add_dll_directory(qt_bin)
        except Exception:
            pass
        os.environ["PATH"] = qt_bin + os.pathsep + os.environ.get("PATH", "")
    try:
        os.add_dll_directory(base_dir)
    except Exception:
        pass
    os.environ["PATH"] = base_dir + os.pathsep + os.environ.get("PATH", "")

# Suppress Qt DPI awareness error on non-admin processes.
# Must be set before any Qt import.
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "0")
os.environ.setdefault("QT_SCALE_FACTOR", "1")

from PyQt6.QtWidgets import QApplication
from PyQt6 import sip
from PyQt6.QtCore import pyqtSignal, QTimer, Qt, QByteArray
from PyQt6.QtGui import QIcon, QCloseEvent
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

from config import Config, get_resource_path
from actions import ActionEngine
from hook import KeyboardHook
from gui import NumpadEditor
from ui.main_window import GlassNumpadEditor
from tray import SystemTrayApp

# IPC socket name — only used to wake up a running instance's window.
# The NAMED MUTEX below is the authoritative single-instance guard.
SOCKET_NAME  = "KeySpark_ShowWindow_IPC"
MUTEX_NAME   = "Local\\KeySpark_SingleInstance_Mutex"

# Kept alive as a global so the OS does not release it while we run.
_g_mutex_handle = None


class LegacyMainWindow(NumpadEditor):
    """
    Subclass of NumpadEditor to orchestrate thread-safe GUI signals,
    window close events (minimize to tray), and clean application exits.
    """
    show_signal = pyqtSignal()
    exit_signal = pyqtSignal()
    tray: SystemTrayApp | None

    def __init__(self, config, hook, ptt=None, overlay=None,
                 screen_engine=None, ipc_server=None):
        super().__init__(config, ptt)
        self.hook         = hook
        self.ptt          = ptt
        self.overlay      = overlay
        self.screen_engine = screen_engine
        self.ipc_server   = ipc_server
        self.tray = None

        if self.ipc_server:
            self.ipc_server.newConnection.connect(self._handle_ipc_connection)

        # Connect thread-safe tray / IPC signals
        self.show_signal.connect(self.show_and_raise)
        self.exit_signal.connect(self.app_exit)

        # ── Hook Watchdog: auto-refresh hook across Windows sleep/lock/inactivity ──
        self._watchdog = QTimer(self)
        self._watchdog.setInterval(10000)  # Refresh hook every 10 seconds
        self._watchdog.timeout.connect(self._watchdog_tick)
        self._watchdog.start()

    def _watchdog_tick(self):
        """Runs on Qt main thread to ensure WH_KEYBOARD_LL remains active if dropped."""
        if hasattr(self, 'hook') and self.hook:
            if not self.hook.is_active:
                print("[App] Watchdog: Hook inactive, reinstalling...")
                self.hook.install()

    def nativeEvent(
        self,
        eventType: QByteArray | bytes | bytearray | memoryview,
        message: sip.voidptr,
    ) -> tuple[bool, sip.voidptr]:
        """Listen for Windows Session Unlock (0x02B1) and Power Resume (0x0218)."""
        if eventType == b"windows_generic_MSG" and message:
            try:
                addr = int(message)
                if addr:
                    msg = ctypes.wintypes.MSG.from_address(addr)
                    if msg.message in (0x02B1, 0x0218):
                        if hasattr(self, 'hook') and self.hook:
                            print(f"[App] Windows session/power event ({msg.message:#x}) — refreshing hook.")
                            self.hook.refresh_hook()
            except Exception:
                pass
        return False, sip.voidptr(0)

    # ── IPC: show-window only ─────────────────────────────────────────────────

    def _handle_ipc_connection(self):
        """
        A second instance tried to start — it sends b'SHOW' to ask us to
        surface our window.  We only act on that exact token; all other
        data (including anything a random process sends) is silently dropped.
        EXIT is intentionally NOT handled here — the only way to quit is via
        the tray 'Exit' menu item or the OS killing our process.
        """
        if self.ipc_server is None:
            return
        conn = self.ipc_server.nextPendingConnection()
        if conn is None:
            return

        def _on_data():
            try:
                data = bytes(conn.readAll()).strip()
                if data == b"SHOW":
                    print("[App] IPC: received SHOW — raising window.")
                    self.show_signal.emit()
                else:
                    # Unknown / untrusted data — ignore completely.
                    print(f"[App] IPC: unexpected data ({data!r}) — ignored.")
            except Exception as e:
                print(f"[App] IPC handler error: {e}")
            finally:
                conn.disconnectFromServer()

        conn.readyRead.connect(_on_data)
        # Guard: if the client disconnects without sending data, just close.
        conn.disconnected.connect(conn.deleteLater)

    # ── Window management ─────────────────────────────────────────────────────

    def show_and_raise(self):
        self.setWindowState(
            (self.windowState() & ~Qt.WindowState.WindowMinimized)
            | Qt.WindowState.WindowActive
        )
        self.showNormal()
        self.show()
        self.activateWindow()
        self.raise_()

    def closeEvent(self, a0: QCloseEvent | None) -> None:
        """Intercept close to hide (tray mode) instead of quitting."""
        if a0:
            a0.ignore()
        self.hide()

    # ── Clean shutdown ────────────────────────────────────────────────────────

    def app_exit(self):
        """Fully shut down — called only from the tray Exit action."""
        print("[App] Shutting down…")
        # Release IPC server so a future instance can start cleanly.
        if self.ipc_server:
            self.ipc_server.close()
        QLocalServer.removeServer(SOCKET_NAME)
        self.hook.uninstall()
        if self.ptt:
            self.ptt.shutdown()
        if self.screen_engine:
            self.screen_engine.force_stop()
        if self.overlay:
            self.overlay.close()
        app = QApplication.instance()
        if app is not None:
            app.quit()


class MainWindow(GlassNumpadEditor):
    """Glass editor with the existing tray, hook watchdog and IPC lifecycle."""
    show_signal = pyqtSignal()
    exit_signal = pyqtSignal()
    numlock_signal = pyqtSignal(bool)
    tray: SystemTrayApp | None

    def __init__(self, config, hook, ptt=None, overlay=None, screen_engine=None, ipc_server=None):
        super().__init__(config, ptt, overlay)
        self.hook = hook
        self.ptt = ptt
        self.overlay = overlay
        self.screen_engine = screen_engine
        self.ipc_server = ipc_server
        self.tray = None
        if ipc_server:
            ipc_server.newConnection.connect(self._handle_ipc_connection)
        self.show_signal.connect(self.show_and_raise)
        self.exit_signal.connect(self.app_exit)
        self.numlock_signal.connect(self._on_numlock_state)
        self._watchdog = QTimer(self)
        self._watchdog.setInterval(10000)
        self._watchdog.timeout.connect(self._watchdog_tick)
        self._watchdog.start()

    def _on_numlock_state(self, macros_active):
        # Low-level hooks run before Windows flips the toggle bit. Read it
        # shortly after the key event has completed so the display matches OS state.
        QTimer.singleShot(25, self._sync_numlock_state)

    def _sync_numlock_state(self):
        macros_active = not bool(ctypes.windll.user32.GetKeyState(0x90) & 1)
        self.set_numlock_state(macros_active)
        if self.config.get_setting("notify_on_toggle", True) and self.overlay:
            self.overlay.show_state(macros_active)
        if self.config.get_setting("notify_sound", False):
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_OK)
            except (ImportError, RuntimeError):
                pass
        tray = self.tray
        if tray:
            tray.set_macros_active(macros_active)

    def _watchdog_tick(self):
        if self.hook and not self.hook.is_active:
            self.hook.install()

    def nativeEvent(
        self,
        eventType: QByteArray | bytes | bytearray | memoryview,
        message: sip.voidptr,
    ) -> tuple[bool, sip.voidptr]:
        if eventType == b"windows_generic_MSG" and message:
            try:
                msg = ctypes.wintypes.MSG.from_address(int(message))
                if msg.message in (0x02B1, 0x0218) and self.hook:
                    self.hook.refresh_hook()
            except Exception:
                pass
        return False, sip.voidptr(0)

    def _handle_ipc_connection(self):
        if not self.ipc_server:
            return
        conn = self.ipc_server.nextPendingConnection()
        if conn is None:
            return
        def _on_data():
            try:
                if bytes(conn.readAll()).strip() == b"SHOW":
                    self.show_signal.emit()
            finally:
                conn.disconnectFromServer()
        conn.readyRead.connect(_on_data)
        conn.disconnected.connect(conn.deleteLater)

    def show_and_raise(self):
        self.setWindowState((self.windowState() & ~Qt.WindowState.WindowMinimized) | Qt.WindowState.WindowActive)
        self.showNormal()
        self.show()
        self.activateWindow()
        self.raise_()

    def closeEvent(self, a0: QCloseEvent | None) -> None:
        if a0 is not None:
            a0.ignore()
        self.hide()

    def app_exit(self):
        if self.ipc_server:
            self.ipc_server.close()
        QLocalServer.removeServer(SOCKET_NAME)
        if self.hook:
            self.hook.uninstall()
        if self.ptt:
            self.ptt.shutdown()
        if self.screen_engine:
            self.screen_engine.force_stop()
        if self.overlay:
            self.overlay.close()
        app = QApplication.instance()
        if app:
            app.quit()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _acquire_mutex():
    """
    Try to acquire the Windows Named Mutex.
    Returns (handle, already_exists).
    The handle must be kept alive for the lifetime of the process.
    """
    handle = ctypes.windll.kernel32.CreateMutexW(None, True, MUTEX_NAME)
    already_exists = (ctypes.windll.kernel32.GetLastError() == 183)
    return handle, already_exists


def _send_show_to_running_instance():
    """
    Tell the already-running instance to surface its window.
    Uses a short-lived QLocalSocket (requires a temporary QApplication).
    """
    try:
        sock = QLocalSocket()
        sock.connectToServer(SOCKET_NAME)
        if sock.waitForConnected(400):
            sock.write(b"SHOW")
            sock.waitForBytesWritten(400)
            sock.disconnectFromServer()
        sock.abort()
    except Exception as e:
        print(f"[App] Could not reach running instance: {e}")


def enable_autostart():
    """Register this exe in Windows startup. Only for compiled EXE builds."""
    import winreg
    if not getattr(sys, "frozen", False):
        print("[Startup] Dev mode — autostart registry NOT modified.")
        return
    try:
        exe_path = sys.executable
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, "KeySpark", 0, winreg.REG_SZ, exe_path)
        winreg.CloseKey(key)
        print(f"[Startup] Autostart registered: {exe_path}")
    except Exception as e:
        print(f"[Startup] Autostart registration failed: {e}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    global _g_mutex_handle

    # ── 1. Set AppUserModelID (cosmetic, non-fatal) ───────────────────────────
    try:
        myappid = "KeySpark.NumpadMacro.1.0"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception as e:
        print(f"[App] AppUserModelID error: {e}")

    # ── 2. Single-instance guard via Named Mutex ──────────────────────────────
    # The OS automatically releases the mutex when the process exits (crash or
    # normal), so there are no stale locks across restarts.
    app = QApplication(sys.argv)          # needed for QLocalSocket below
    app.setQuitOnLastWindowClosed(False)

    _g_mutex_handle, already_running = _acquire_mutex()

    if already_running:
        print("[App] Another instance is running — asking it to show its window.")
        _send_show_to_running_instance()
        sys.exit(0)

    # ── 3. Autostart registration (EXE-only) ──────────────────────────────────
    try:
        enable_autostart()
    except Exception as e:
        print(f"[Startup] Autostart error: {e}")

    # ── 4. IPC server for show-window requests from future launches ───────────
    QLocalServer.removeServer(SOCKET_NAME)   # clean any stale pipe from crash
    ipc_server = QLocalServer()
    if not ipc_server.listen(SOCKET_NAME):
        print(f"[App] IPC server could not listen: {ipc_server.errorString()}")

    # ── 5. Application icon ───────────────────────────────────────────────────
    icon_path = get_resource_path("app_icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # ── 6. Core subsystems ────────────────────────────────────────────────────
    config = Config()

    from ptt_engine  import PTTEngine
    from ui.overlays import OverlayPill
    app_appearance = str(config.get_setting("appearance", "system") or "system")
    overlay    = OverlayPill(app_appearance)
    ptt_engine = PTTEngine(config=config, overlay=overlay)

    action_engine = ActionEngine()
    action_engine.set_ptt(ptt_engine, overlay)

    from screen_engine import ScreenEngine
    from flash_overlay import ScreenFlashOverlay
    flash_overlay = ScreenFlashOverlay()
    screen_engine = ScreenEngine(config=config, overlay=overlay,
                                  flash_overlay=flash_overlay)
    action_engine.set_screen_engine(screen_engine)

    hook = KeyboardHook(config, action_engine, ptt_engine)

    # ── 7. Main window + tray ─────────────────────────────────────────────────
    if config.get_setting("theme", "glass") == "neo":
        main_window = LegacyMainWindow(config, hook, ptt_engine, overlay, screen_engine, ipc_server=ipc_server)
        hook.gui_notifier = main_window.trigger_physical_key_press
    else:
        main_window = MainWindow(config, hook, ptt_engine, overlay, screen_engine, ipc_server=ipc_server)
        hook.gui_notifier = main_window.trigger_physical_key_press
        hook.numlock_notifier = main_window.numlock_signal.emit
        main_window.set_numlock_state(not bool(ctypes.windll.user32.GetKeyState(0x90) & 1), animate=False)

    tray_icon_path = get_resource_path(os.path.join("assets", "icon.png"))
    if not os.path.exists(tray_icon_path) and os.path.exists(icon_path):
        tray_icon_path = icon_path

    tray = SystemTrayApp(
        icon_path=tray_icon_path,
        on_show_gui=lambda: main_window.show_signal.emit(),
        on_exit=lambda: main_window.exit_signal.emit()
    )
    tray.start()
    main_window.tray = tray
    if hasattr(main_window, "_macros_active"):
        tray.set_macros_active(getattr(main_window, "_macros_active", False))

    main_window.show()

    # ── 8. Install keyboard hook after event loop starts ─────────────────────
    # WH_KEYBOARD_LL requires the installing thread to have a running message
    # pump. Qt's exec() loop is that pump.
    QTimer.singleShot(0, hook.install)

    # ── 9. Run ────────────────────────────────────────────────────────────────
    code = app.exec()
    sys.exit(code)


if __name__ == "__main__":
    main()
