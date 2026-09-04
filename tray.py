import pystray
from PIL import Image
import threading
import os

class SystemTrayApp:
    """
    Manages the background system tray icon using pystray.
    Calls callbacks to control the main PyQt6 interface.
    """
    def __init__(self, icon_path: str, on_show_gui, on_exit):
        self.icon_path = icon_path
        self.on_show_gui = on_show_gui
        self.on_exit = on_exit
        self.icon = None

    def start(self):
        # Load or generate icon image
        if os.path.exists(self.icon_path):
            try:
                image = Image.open(self.icon_path)
            except Exception as e:
                print(f"[Tray] Error loading icon path, using fallback: {e}")
                image = self._create_fallback_image()
        else:
            image = self._create_fallback_image()

        # Build menu
        menu = pystray.Menu(
            pystray.MenuItem("Configure...", self._show_gui_action, default=True),
            pystray.MenuItem("Exit", self._exit_action)
        )

        self.icon = pystray.Icon("Micro Action", image, "Micro Action", menu)
        
        # Start pystray event loop in a daemon thread
        threading.Thread(target=self.icon.run, daemon=True).start()

    def _create_fallback_image(self):
        # Create solid orange square as fallback
        return Image.new("RGB", (64, 64), color=(250, 179, 135))

    def _show_gui_action(self, icon=None, item=None):
        if self.on_show_gui:
            self.on_show_gui()

    def _exit_action(self, icon=None, item=None):
        if self.icon:
            self.icon.stop()
        if self.on_exit:
            self.on_exit()
