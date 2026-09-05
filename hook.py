import ctypes
import ctypes.wintypes
import threading
import queue

VK_TO_POS = {
    0x24: "num7",    # VK_HOME
    0x26: "num8",    # VK_UP
    0x21: "num9",    # VK_PRIOR
    0x25: "num4",    # VK_LEFT
    0x0C: "num5",    # VK_CLEAR
    0x27: "num6",    # VK_RIGHT
    0x23: "num1",    # VK_END
    0x28: "num2",    # VK_DOWN
    0x22: "num3",    # VK_NEXT
    0x2D: "num0",    # VK_INSERT
    0x2E: "numdot",  # VK_DELETE
}

# Scan codes that belong exclusively to numpad (without E0 extended prefix).
# Regular nav cluster sends the same scan codes WITH E0 prefix → extended=True.
NUMPAD_SCANCODES = {0x47,0x48,0x49,0x4B,0x4C,0x4D,0x4F,0x50,0x51,0x52,0x53}

class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode",      ctypes.c_ulong),
        ("scanCode",    ctypes.c_ulong),
        ("flags",       ctypes.c_ulong),
        ("time",        ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_ulong * 2),
    ]


# Define hook procedure type with correct 64-bit Win32 types at module level
HOOKPROC = ctypes.WINFUNCTYPE(
    ctypes.c_longlong, # LRESULT
    ctypes.c_int,
    ctypes.wintypes.WPARAM,
    ctypes.wintypes.LPARAM
)

class KeyboardHook:
    """
    Installs WH_KEYBOARD_LL on the CALLING thread (must be the Qt main thread).
    The Qt event loop acts as the required message pump — no separate thread needed.
    A dedicated worker thread handles PTT/action dispatch so the callback stays fast.
    """

    def __init__(self, config, action_engine, ptt_engine):
        self.config         = config
        self.action_engine  = action_engine
        self.ptt_engine     = ptt_engine
        self.gui_notifier   = None
        self.hook_id        = None
        self.pointer        = None          # keep WINFUNCTYPE alive

        self._event_queue   = queue.Queue()
        self._stop_event    = threading.Event()
        self._worker        = None

        self._ptt_active_key = None
        self._pressed_keys   = set()

    # ── Public API ───────────────────────────────────────────────────────────

    def install(self):
        """Call this from the Qt main thread AFTER QApplication.exec() starts
        (e.g. via a QTimer.singleShot(0, hook.install) in main)."""
        self._stop_event.clear()

        # Start worker BEFORE installing hook
        if self._worker is None or not self._worker.is_alive():
            self._worker = threading.Thread(
                target=self._worker_loop, daemon=True, name="HookWorker")
            self._worker.start()

        user32 = ctypes.windll.user32
        self.pointer = HOOKPROC(self._hook_callback)

        # Set explicit argument and return types for the Win32 hook APIs
        user32.SetWindowsHookExW.argtypes = [
            ctypes.c_int,
            HOOKPROC,
            ctypes.wintypes.HINSTANCE,
            ctypes.wintypes.DWORD
        ]
        user32.SetWindowsHookExW.restype = ctypes.wintypes.HHOOK

        user32.UnhookWindowsHookEx.argtypes = [ctypes.wintypes.HHOOK]
        user32.UnhookWindowsHookEx.restype = ctypes.wintypes.BOOL

        user32.CallNextHookEx.argtypes = [
            ctypes.wintypes.HHOOK,
            ctypes.c_int,
            ctypes.wintypes.WPARAM,
            ctypes.wintypes.LPARAM
        ]
        user32.CallNextHookEx.restype = ctypes.c_longlong # LRESULT

        self.hook_id = user32.SetWindowsHookExW(13, self.pointer, None, 0)

        if not self.hook_id:
            err = ctypes.windll.kernel32.GetLastError()
            msg = {5: "Run as Administrator", 126: "hMod must be None"}.get(err, "")
            print(f"[Hook] FAILED — error {err}. {msg}")
        else:
            print(f"[Hook] Installed on main thread (id={self.hook_id})")

    def refresh_hook(self):
        """
        Re-registers WH_KEYBOARD_LL with Windows User32.
        Called on session unlock, resume from sleep, or periodic watchdog timer.
        Must run on the Qt main thread.
        """
        if self.pointer:
            user32 = ctypes.windll.user32
            if self.hook_id:
                try:
                    user32.UnhookWindowsHookEx(self.hook_id)
                except Exception:
                    pass
                self.hook_id = None
            self.hook_id = user32.SetWindowsHookExW(13, self.pointer, None, 0)
            if not self.hook_id:
                err = ctypes.windll.kernel32.GetLastError()
                print(f"[Hook] Watchdog re-hook FAILED — error {err}")

    def uninstall(self):
        """Call from main thread."""
        if self.hook_id:
            ctypes.windll.user32.UnhookWindowsHookEx(self.hook_id)
            self.hook_id = None
        self._stop_event.set()
        self._event_queue.put(None)
        if self._worker:
            self._worker.join(timeout=2.0)
        print("[Hook] Uninstalled.")

    @property
    def is_active(self):
        return bool(self.hook_id)

    # ── Callback — runs on Qt main thread, must return in < 300 ms ──────────

    def _hook_callback(self, nCode, wParam, lParam):
        try:
            if nCode < 0:
                return ctypes.windll.user32.CallNextHookEx(
                    self.hook_id, nCode, wParam, lParam)

            # NumLock ON → pass everything through
            if ctypes.windll.user32.GetKeyState(0x90) & 1:
                return ctypes.windll.user32.CallNextHookEx(
                    self.hook_id, nCode, wParam, lParam)

            if not lParam:
                return ctypes.windll.user32.CallNextHookEx(
                    self.hook_id, nCode, wParam, lParam)

            kbd = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents

            # Distinguish numpad from nav-cluster:
            #   LLKHF_EXTENDED (bit 0) is SET for nav-cluster, CLEAR for numpad.
            #   Scan code must also be in the numpad range as a secondary check.
            #   Injected keys (bit 4) are ignored to avoid feedback loops.
            is_extended = bool(kbd.flags & 0x01)
            is_injected = bool(kbd.flags & 0x10)

            pos_id = VK_TO_POS.get(kbd.vkCode)

            if (pos_id
                    and not is_extended
                    and not is_injected
                    and kbd.scanCode in NUMPAD_SCANCODES):

                action = self.config.get_action(pos_id)
                if action:
                    try:
                        self._event_queue.put_nowait((wParam, pos_id, action))
                    except queue.Full:
                        pass
                    return 1    # suppress key
        except Exception as e:
            # Guard against any unexpected exception reaching Windows User32
            pass

        return ctypes.windll.user32.CallNextHookEx(
            self.hook_id, nCode, wParam, lParam)

    # ── Worker thread — does actual work off the hot callback path ───────────

    def _worker_loop(self):
        while not self._stop_event.is_set():
            try:
                item = self._event_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if item is None:
                break

            try:
                wParam, pos_id, action = item
                is_down = wParam in (0x0100, 0x0104)
                is_up   = wParam in (0x0101, 0x0105)
                is_ptt  = action.get("type") == "ptt"

                if is_down:
                    if is_ptt:
                        if self._ptt_active_key is None:
                            self._ptt_active_key = pos_id
                            print(f"[Hook] PTT START -> {pos_id}")
                            if self.ptt_engine:
                                self.ptt_engine.start(config_val=action.get("value", "base"))
                    else:
                        if pos_id not in self._pressed_keys:
                            self._pressed_keys.add(pos_id)
                            print(f"[Hook] Action -> {pos_id}: {action}")
                            self.action_engine.dispatch(action)

                    # Trigger GUI notification and keypress feedback
                    if self.gui_notifier:
                        try:
                            self.gui_notifier(pos_id)
                        except Exception as e:
                            print(f"[Hook] GUI notifier error: {e}")
                elif is_up:
                    if is_ptt:
                        if self._ptt_active_key == pos_id:
                            self._ptt_active_key = None
                            print(f"[Hook] PTT STOP -> {pos_id}")
                            if self.ptt_engine:
                                self.ptt_engine.stop()
                    else:
                        self._pressed_keys.discard(pos_id)
            except Exception as e:
                print(f"[Hook Worker Error] {e}")
