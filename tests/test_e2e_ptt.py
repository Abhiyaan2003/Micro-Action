"""
End-to-end PTT integration test.
Simulates exactly what happens when you hold a numpad key in the full app.
Run with: python -X utf8 test_e2e_ptt.py
"""
import sys
import os
import time
import threading
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

print("=" * 55)
print("  END-TO-END PTT INTEGRATION TEST")
print("=" * 55)

# ── Step 1: Config ───────────────────────────────────────
print("\n[1/5] Loading config...")
from config import Config
config = Config()
config.set_action("num0", {"type": "ptt", "value": ""})
config.save()
print(f"  OK — PTT action set on num0: {config.get_action('num0')}")

# ── Step 2: PTTEngine init (no overlay) ─────────────────
print("\n[2/5] Initialising PTTEngine (no overlay)...")
from ptt_engine import PTTEngine
ptt = PTTEngine(config=config, overlay=None)

# Wait for model to load (up to 30s)
print("  Waiting for Whisper model to load...", end="", flush=True)
for _ in range(60):
    if ptt.model_loaded:
        break
    print(".", end="", flush=True)
    time.sleep(0.5)

if not ptt.model_loaded:
    print("\n  FAIL: Model did not load within 30s")
    sys.exit(1)
print(f"\n  OK — Model loaded.")

# ── Step 3: Simulate PTT start/stop ─────────────────────
print("\n[3/5] Simulating PTT key hold (5 seconds)...")
print("      >>> SPEAK NOW — say something clearly <<<")
ptt.start()

if not ptt._running:
    print("  FAIL: PTT engine did not start!")
    sys.exit(1)
print(f"  OK — PTT running: {ptt._running}")

time.sleep(5)

print("\n  Stopping PTT (simulating key release)...")
ptt.stop()
print(f"  OK — PTT stopped: {not ptt._running}")

# ── Step 4: Clipboard paste test ────────────────────────
print("\n[4/5] Testing clipboard paste mechanism...")
import win32clipboard, win32con

# Backup
old = None
try:
    win32clipboard.OpenClipboard()
    if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
        old = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
    win32clipboard.CloseClipboard()
    print(f"  Backed up clipboard: {repr(old[:40]) if old else 'empty'}")
except Exception as e:
    print(f"  WARNING: Clipboard backup failed: {e}")

# Write test text
test_text = "PTT_TEST_STRING_12345"
try:
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, test_text)
    win32clipboard.CloseClipboard()
    # Read back to verify
    win32clipboard.OpenClipboard()
    result = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
    win32clipboard.CloseClipboard()
    if result == test_text:
        print(f"  OK — Clipboard write/read verified: '{result}'")
    else:
        print(f"  FAIL: Clipboard mismatch — wrote '{test_text}', got '{result}'")
except Exception as e:
    print(f"  FAIL: Clipboard error: {e}")

# Restore
if old is not None:
    try:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, old)
        win32clipboard.CloseClipboard()
        print("  OK — Clipboard restored")
    except Exception as e:
        print(f"  WARNING: Restore failed: {e}")

# ── Step 5: Check last transcription ────────────────────
print("\n[5/5] Checking what PTT engine transcribed...")
# The engine types directly — we check internal state
print(f"  _typed_so_far = '{ptt._typed_so_far}'")
if ptt._typed_so_far:
    print(f"  OK — Text was transcribed and typed: '{ptt._typed_so_far}'")
else:
    print("  WARNING: Nothing was typed.")
    print("  This is EXPECTED if Notepad or a text field was not focused.")
    print("  The text would have been typed into whatever window was active.")
    print("  To test typing: open Notepad, then hold a numpad key in the full app.")

print("\n" + "=" * 55)
print("  TEST COMPLETE")
print("=" * 55)
