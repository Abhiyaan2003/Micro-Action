"""
PHYSICAL KEY TEST
Runs hook with GetMessageW pump, waits 10s for real keystrokes.
Press: arrow keys, Home/End/Delete, then Numpad keys with NumLock OFF.
Results saved to hook_debug.txt
"""
import sys, os, ctypes, ctypes.wintypes, time, threading
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("vkCode",ctypes.c_ulong),("scanCode",ctypes.c_ulong),
                ("flags",ctypes.c_ulong),("time",ctypes.c_ulong),
                ("dwExtraInfo",ctypes.c_ulong*2)]

log = []
hook_id = None
thread_id_holder = [None]
ready = threading.Event()

def cb(nCode, wParam, lParam):
    if nCode >= 0 and wParam == 0x100:  # keydown only
        kbd = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
        ext = bool(kbd.flags & 1)
        inj = bool(kbd.flags & 0x10)
        nl  = bool(ctypes.windll.user32.GetKeyState(0x90) & 1)
        line = (f"VK=0x{kbd.vkCode:02X} SC=0x{kbd.scanCode:02X} "
                f"ext={int(ext)} inj={int(inj)} numlock={int(nl)}")
        log.append(line)
        print(f"  {line}")
    return ctypes.windll.user32.CallNextHookEx(hook_id, nCode, wParam, lParam)

CMPFUNC = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_void_p)
ptr = CMPFUNC(cb)

def pump():
    global hook_id
    thread_id_holder[0] = ctypes.windll.kernel32.GetCurrentThreadId()
    u = ctypes.windll.user32
    u.SetWindowsHookExW.restype = ctypes.wintypes.HHOOK
    hook_id = u.SetWindowsHookExW(13, ptr, None, 0)
    ready.set()
    msg = ctypes.wintypes.MSG()
    while True:
        r = u.GetMessageW(ctypes.byref(msg), None, 0, 0)
        if r <= 0: break
        u.TranslateMessage(ctypes.byref(msg))
        u.DispatchMessageW(ctypes.byref(msg))
    u.UnhookWindowsHookEx(hook_id)

t = threading.Thread(target=pump, daemon=True)
t.start()
ready.wait()

print(f"Hook ready (id={hook_id}). You have 10 seconds.")
print("Press: UP, DOWN, HOME, END, DELETE arrows, then Numpad keys (NumLock OFF)")
print()

for i in range(10, 0, -1):
    print(f"\r  {i}s remaining... ({len(log)} keys captured)", end="", flush=True)
    time.sleep(1)

print(f"\n\nDone. {len(log)} keydowns captured.")
ctypes.windll.user32.PostThreadMessageW(thread_id_holder[0], 0x0012, 0, 0)
t.join(timeout=1)

out_file = os.path.join(os.path.dirname(__file__), "hook_debug.txt")
with open(out_file, "w") as f:
    f.write("\n".join(log))

print("\n=== RESULTS ===")
for l in log:
    print(" ", l)
print(f"\nSaved to {out_file}")
