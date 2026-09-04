import subprocess
import ctypes


class ActionEngine:
    def __init__(self):
        self.overlay = None
        self.ptt_engine = None
        self.screen_engine = None

    def set_ptt(self, ptt_engine, overlay):
        self.ptt_engine = ptt_engine
        self.overlay = overlay

    def set_screen_engine(self, screen_engine):
        self.screen_engine = screen_engine

    def dispatch(self, action: dict, event_type: str = "down"):
        t = action.get("type")
        v = action.get("value", "")

        if t == "ptt":
            if self.ptt_engine:
                if event_type == "down":
                    self.ptt_engine.start()
                else:
                    self.ptt_engine.stop()
            return

        if event_type != "down":
            return  # Other actions only trigger on key down

        if t == "hotkey":
            self.send_hotkey(v)
        elif t == "website":
            self.launch_website(v)
        elif t == "launch":
            self.launch_app(v)
        elif t == "script":
            self.run_script(v)
        elif t == "screenshot":
            if self.screen_engine:
                self.screen_engine.take_screenshot(v)
        elif t == "screenrec":
            if self.screen_engine:
                self.screen_engine.toggle_recording(v)

    def send_hotkey(self, keys: str):
        import pyautogui
        # pyautogui needs keys split by '+'
        parts = [k.strip().lower() for k in keys.split("+")]
        # Replace common GUI modifier names to match pyautogui
        mods = {
            "win": "win",
            "cmd": "win",
            "ctrl": "ctrl",
            "control": "ctrl",
            "alt": "alt",
            "shift": "shift"
        }
        mapped_parts = [mods.get(p, p) for p in parts]
        try:
            pyautogui.hotkey(*mapped_parts)
        except Exception as e:
            print(f"[Actions] Hotkey error with {mapped_parts}: {e}")

    def launch_app(self, path: str):
        try:
            # shell=True enables launching programs, URLs, or shell verbs
            subprocess.Popen(path, shell=True)
        except Exception as e:
            print(f"[Actions] App launch error for '{path}': {e}")

    def launch_website(self, val: str):
        try:
            if "|" in val:
                browser, url = val.split("|", 1)
            else:
                browser, url = "default", val

            # Normalize url (ensure it starts with http:// or https://)
            if not url.startswith(("http://", "https://")):
                url = "https://" + url

            browser = browser.lower()
            if browser == "chrome":
                subprocess.Popen(["cmd.exe", "/c", f"start chrome.exe {url}"], shell=True)
            elif browser == "firefox":
                subprocess.Popen(["cmd.exe", "/c", f"start firefox.exe {url}"], shell=True)
            elif browser == "edge":
                subprocess.Popen(["cmd.exe", "/c", f"start msedge.exe {url}"], shell=True)
            elif browser == "brave":
                subprocess.Popen(["cmd.exe", "/c", f"start brave.exe {url}"], shell=True)
            else:
                # Default browser fallback
                import webbrowser
                webbrowser.open(url)
        except Exception as e:
            print(f"[Actions] Website launch error for '{val}': {e}")

    def run_script(self, path: str):
        try:
            # Prevent console window flashing using CREATE_NO_WINDOW (0x08000000)
            CREATE_NO_WINDOW = 0x08000000
            if path.endswith(".ps1"):
                subprocess.Popen(
                    ["powershell", "-ExecutionPolicy", "Bypass", "-File", path],
                    creationflags=CREATE_NO_WINDOW
                )
            elif path.endswith(".bat") or path.endswith(".cmd"):
                subprocess.Popen(
                    path,
                    shell=True,
                    creationflags=CREATE_NO_WINDOW
                )
            elif path.endswith(".py"):
                subprocess.Popen(
                    ["python", path],
                    creationflags=CREATE_NO_WINDOW
                )
            else:
                # Fallback launch
                subprocess.Popen(path, shell=True)
        except Exception as e:
            print(f"[Actions] Script run error for '{path}': {e}")
