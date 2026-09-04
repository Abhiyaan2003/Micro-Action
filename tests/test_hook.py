"""
Hook diagnostic — press numpad keys to see what VK codes and flags they produce.
Run with: python -X utf8 test_hook.py
Press numpad keys (with NumLock OFF) to see their codes.
Press Ctrl+C or close window to stop.
"""
import sys
import os
import ctypes
import ctypes.wintypes
import time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode",      ctypes.c_ulong),
        ("scanCode",    ctypes.c_ulong),
        ("flags",       ctypes.c_ulong),
        ("time",        ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
    ]

VK_NAMES = {
    0x24: "VK_HOME    -> num7",
    0x26: "VK_UP      -> num8",
    0x21: "VK_PRIOR   -> num9",
    0x25: "VK_LEFT    -> num4",
    0x0C: "VK_CLEAR   -> num5",
    0x27: "VK_RIGHT   -> num6",
    0x23: "VK_END     -> num1",
    0x28: "VK_DOWN    -> num2",
    0x22: "VK_NEXT    -> num3",
    0x2D: "VK_INSERT  -> num0",
    0x2E: "VK_DELETE  -> numdot",
    0x60: "VK_NUMPAD0 (NumLock ON)",
    0x61: "VK_NUMPAD1 (NumLock ON)",
    0x62: "VK_NUMPAD2 (NumLock ON)",
    0x63: "VK_NUMPAD3 (NumLock ON)",
    0x64: "VK_NUMPAD4 (NumLock ON)",
    0x65: "VK_NUMPAD5 (NumLock ON)",
    0x66: "VK_NUMPAD6 (NumLock ON)",
    0x67: "VK_NUMPAD7 (NumLock ON)",
    0x68: "VK_NUMPAD8 (NumLock ON)",
    0x69: "VK_NUMPAD9 (NumLock ON)",
    0x6E: "VK_DECIMAL -> numdot (NumLock ON)",
}

WM_NAMES = {
    0x0100: "KEYDOWN",
    0x0101: "KEYUP",
    0x0104: "SYSKEYDOWN",
    0x0105: "SYSKEYUP",
}

hook_id = None

def hook_callback(nCode, wParam, lParam):
    if nCode >= 0:
        kbd = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
        vk = kbd.vkCode
        is_ext = bool(kbd.flags & 1)
        event = WM_NAMES.get(wParam, f"0x{wParam:04X}")
        numlock = bool(ctypes.windll.user32.GetKeyState(0x90) & 1)
        name = VK_NAMES.get(vk, f"VK=0x{vk:02X} (unknown)")
        
        # Only print on keydown to avoid spam
        if wParam in (0x0100, 0x0104):
            intercepted = (not numlock) and (not is_ext) and (vk in VK_NAMES)
            marker = " <-- INTERCEPTED by hook" if intercepted else ""
            print(f"  {event:<10} VK=0x{vk:02X}  Extended={is_ext}  NumLock={'ON' if numlock else 'OFF'}  -> {name}{marker}")
    
    return ctypes.windll.user32.CallNextHookEx(hook_id, nCode, wParam, lParam)

CMPFUNC = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_void_p)
pointer = CMPFUNC(hook_callback)

hook_id = ctypes.windll.user32.SetWindowsHookExW(
    13,  # WH_KEYBOARD_LL
    pointer,
    ctypes.windll.kernel32.GetModuleHandleW(None),
    0
)

if not hook_id:
    print("FAIL: Could not install hook (try running as Administrator)")
    sys.exit(1)

print("=" * 55)
print("  HOOK DIAGNOSTIC — press numpad keys now")
print("  Turn NumLock OFF for macro mode")
print("  Ctrl+C to quit")
print("=" * 55)

msg = ctypes.wintypes.MSG()
try:
    while True:
        ret = ctypes.windll.user32.PeekMessageW(ctypes.byref(msg), 0, 0, 0, 1)
        if ret:
            ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
            ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))
        time.sleep(0.01)
except KeyboardInterrupt:
    pass
finally:
    ctypes.windll.user32.UnhookWindowsHookEx(hook_id)
    print("\nHook removed.")
