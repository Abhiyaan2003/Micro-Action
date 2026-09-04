"""
End-to-end test for screenshot and screen recording features.
Tests the ScreenEngine directly without needing the full app running.
"""
import sys
import os
import time
import threading
import io

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Suppress Qt DPI warnings
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "0")
os.environ.setdefault("QT_SCALE_FACTOR", "1")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from config import Config
from ptt_overlay import PTTOverlay
from screen_engine import ScreenEngine

results = []


def log(test_name, passed, detail=""):
    tag = "PASS" if passed else "FAIL"
    results.append((test_name, passed))
    msg = f"  [{tag}] {test_name}"
    if detail:
        msg += f" -- {detail}"
    print(msg)


def run_tests(overlay):
    print("\n" + "=" * 60)
    print("  SCREEN CAPTURE FEATURE -- TEST SUITE")
    print("=" * 60)

    config = Config()
    engine = ScreenEngine(config=config, overlay=overlay)

    # -- Test 1: Screenshot (fullscreen, save to disk) --
    print("\n-- Test 1: Fullscreen Screenshot --")
    test_dir = os.path.join(os.path.dirname(__file__), "_test_captures")
    os.makedirs(test_dir, exist_ok=True)

    config.data.setdefault("capture_settings", {})
    config.data["capture_settings"]["screenshot_dir"] = test_dir

    engine.take_screenshot("fullscreen|clipboard=true|save=true|sound=false|open=false")
    time.sleep(2)

    png_files = [f for f in os.listdir(test_dir) if f.startswith("screenshot_") and f.endswith(".png")]
    log("Fullscreen screenshot saved", len(png_files) >= 1, f"Found {len(png_files)} file(s)")

    if png_files:
        fpath = os.path.join(test_dir, png_files[0])
        fsize = os.path.getsize(fpath)
        log("Screenshot file size > 0", fsize > 0, f"{fsize:,} bytes")

        with open(fpath, "rb") as f:
            header = f.read(8)
        log("Valid PNG header", header[:4] == b'\x89PNG')

    # -- Test 2: Screenshot clipboard copy --
    print("\n-- Test 2: Clipboard Copy --")
    try:
        import win32clipboard
        win32clipboard.OpenClipboard()
        CF_DIB = 8
        has_dib = win32clipboard.IsClipboardFormatAvailable(CF_DIB)
        win32clipboard.CloseClipboard()
        log("Image copied to clipboard (DIB)", has_dib)
    except Exception as e:
        log("Clipboard check", False, str(e))

    # -- Test 3: Primary monitor screenshot --
    print("\n-- Test 3: Primary Monitor Screenshot --")
    engine.take_screenshot("primary|clipboard=false|save=true|sound=false|open=false")
    time.sleep(2)

    png_files_after = [f for f in os.listdir(test_dir) if f.startswith("screenshot_") and f.endswith(".png")]
    log("Primary monitor screenshot saved", len(png_files_after) >= 2, f"{len(png_files_after)} total files")

    # -- Test 4: Active window screenshot --
    print("\n-- Test 4: Active Window Screenshot --")
    engine.take_screenshot("active_window|clipboard=false|save=true|sound=false|open=false")
    time.sleep(2)

    png_files_final = [f for f in os.listdir(test_dir) if f.startswith("screenshot_") and f.endswith(".png")]
    log("Active window screenshot saved", len(png_files_final) >= 3, f"{len(png_files_final)} total files")

    # -- Test 5: Screen Recording (3-second clip) --
    print("\n-- Test 5: Screen Recording (3s clip) --")
    config.data["capture_settings"]["recording_dir"] = test_dir

    log("Initial state is IDLE", engine._rec_state == "idle")

    engine.toggle_recording("fullscreen|fps=15")
    time.sleep(0.5)
    log("State changed to RECORDING", engine._rec_state == "recording")
    log("is_recording property", engine.is_recording)

    time.sleep(3)

    engine.toggle_recording("fullscreen|fps=15")
    time.sleep(0.5)
    log("Stop signal sent (FINALIZING)", engine._rec_state in ("finalizing", "idle"))

    time.sleep(3)
    log("State returned to IDLE", engine._rec_state == "idle")

    mp4_files = [f for f in os.listdir(test_dir) if f.startswith("recording_") and f.endswith(".mp4")]
    log("Recording file created", len(mp4_files) >= 1, f"Found {len(mp4_files)} file(s)")

    if mp4_files:
        rpath = os.path.join(test_dir, mp4_files[0])
        rsize = os.path.getsize(rpath)
        log("Recording file size > 0", rsize > 0, f"{rsize:,} bytes")

    # -- Test 6: Toggle idempotency (double-stop is safe) --
    print("\n-- Test 6: Double-stop safety --")
    engine.toggle_recording("fullscreen|fps=15")
    time.sleep(1)
    engine.toggle_recording("fullscreen|fps=15")  # stop
    time.sleep(3)
    engine.toggle_recording("fullscreen|fps=15")  # should start new
    time.sleep(0.5)
    is_rec = engine.is_recording
    engine.toggle_recording("fullscreen|fps=15")  # stop again
    time.sleep(3)
    log("Toggle idempotency (re-startable)", is_rec)
    log("Final state is IDLE", engine._rec_state == "idle")

    # -- Test 7: Value parser --
    print("\n-- Test 7: Value Parser --")
    opts = engine._parse_value("fullscreen|clipboard=true|save=false|fps=30")
    log("Parse mode", opts.get("mode") == "fullscreen")
    log("Parse clipboard", opts.get("clipboard") == "true")
    log("Parse save", opts.get("save") == "false")
    log("Parse fps", opts.get("fps") == "30")

    opts_empty = engine._parse_value("")
    log("Parse empty string", opts_empty == {})

    # -- Test 8: GUI action types registered --
    print("\n-- Test 8: GUI Integration --")
    from gui import ACTION_THEMES, ACTION_ICONS, MODE_MAP
    log("screenshot in ACTION_THEMES", "screenshot" in ACTION_THEMES)
    log("screenrec in ACTION_THEMES", "screenrec" in ACTION_THEMES)
    log("screenshot in ACTION_ICONS", "screenshot" in ACTION_ICONS)
    log("screenrec in ACTION_ICONS", "screenrec" in ACTION_ICONS)
    log("MODE_MAP has 3 modes", len(MODE_MAP) == 3)

    # -- Test 9: ActionEngine dispatch --
    print("\n-- Test 9: ActionEngine Dispatch --")
    from actions import ActionEngine
    ae = ActionEngine()
    ae.set_screen_engine(engine)
    log("screen_engine wired", ae.screen_engine is engine)

    try:
        ae.dispatch({"type": "screenshot", "value": "fullscreen|clipboard=false|save=false|sound=false"})
        time.sleep(1)
        log("Dispatch screenshot action", True)
    except Exception as e:
        log("Dispatch screenshot action", False, str(e))

    # -- Summary --
    print("\n" + "=" * 60)
    passed = sum(1 for _, p in results if p)
    total = len(results)
    print(f"  RESULTS: {passed}/{total} passed")
    if passed == total:
        print("  ALL TESTS PASSED!")
    else:
        failed = [name for name, p in results if not p]
        print(f"  FAILED: {', '.join(failed)}")
    print("=" * 60)

    print(f"\nTest artifacts in: {test_dir}")
    for f in os.listdir(test_dir):
        print(f"   {f} ({os.path.getsize(os.path.join(test_dir, f)):,} bytes)")

    QApplication.instance().quit()


def main():
    app = QApplication(sys.argv)
    overlay = PTTOverlay()

    QTimer.singleShot(500, lambda: threading.Thread(
        target=run_tests, args=(overlay,), daemon=True).start())

    app.exec()


if __name__ == "__main__":
    main()
