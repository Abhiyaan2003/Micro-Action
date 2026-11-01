import json
import os
import sys

def get_resource_path(relative_path: str) -> str:
    """
    Get absolute path to resource, works for dev and PyInstaller bundle.
    """
    if getattr(sys, 'frozen', False):
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    path = os.path.join(base_path, relative_path)
    if not os.path.exists(path):
        exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else base_path
        path = os.path.join(exe_dir, relative_path)
    return path



DEFAULT_CONFIG_PATH = os.path.join(
    os.getenv("APPDATA", ""), "NumpadMacroPad", "config.json"
)

class Config:
    """
    Manages JSON configuration stored at %APPDATA%/NumpadMacroPad/config.json.
    
    PTT action configuration schema:
        "num5": {
            "type": "ptt",
            "value": "base"  # whisper model size: tiny, base, small, medium, large-v3
        }
    """
    def __init__(self, path=DEFAULT_CONFIG_PATH):
        self.path = path
        self.data = {"keys": {}}
        self.load()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception as e:
                print(f"[Config] Error loading config: {e}. Starting with empty config.")
                self.data = {"keys": {}}
        else:
            self.data = {"keys": {}}

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
            print(f"[Config] Saved to {self.path}")
        except Exception as e:
            print(f"[Config] Error saving config: {e}")

    def get_action(self, pos_id: str) -> dict | None:
        return self.data.get("keys", {}).get(pos_id)

    def set_action(self, pos_id: str, action: dict | None):
        self.data.setdefault("keys", {})
        if action is None:
            self.data["keys"].pop(pos_id, None)
        else:
            self.data["keys"][pos_id] = action

    def get_setting(self, key: str, default=None):
        """Read an optional preference without changing legacy config files."""
        defaults = {
            "theme": "glass",
            "appearance": "system",
            "notify_on_toggle": True,
            "notify_sound": False,
        }
        return self.data.get(key, defaults.get(key, default))

    def set_setting(self, key: str, value):
        """Persist an optional top-level setting while retaining existing keys."""
        self.data[key] = value

