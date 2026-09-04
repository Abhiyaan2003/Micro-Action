"""
Screen Capture Engine — handles screenshot capture and screen recording.

Screenshot: instant capture on key press
Screen Recording: toggle start/stop with frame capture loop + MP4 encoding
"""
import threading
import time
import os
import ctypes
import ctypes.wintypes
from datetime import datetime

DEFAULT_SCREENSHOT_DIR = os.path.join(os.path.expanduser("~"), "Pictures", "Micro Action", "Screenshots")
DEFAULT_RECORDING_DIR = os.path.join(os.path.expanduser("~"), "Videos", "Micro Action", "Recordings")


class ScreenEngine:
    """
    Manages screenshot capture and screen recording.
    
    Screenshot: fire-and-forget capture
    Recording: state machine (IDLE → RECORDING → FINALIZING → IDLE)
    """
    IDLE = "idle"
    RECORDING = "recording"
    FINALIZING = "finalizing"

    def __init__(self, config=None, overlay=None, flash_overlay=None):
        self.config = config
        self.overlay = overlay
        self.flash_overlay = flash_overlay
        self._rec_state = self.IDLE
        self._rec_thread = None
        self._stop_rec = threading.Event()
        self._stop_timer = threading.Event()
        self._rec_start_time = None
        self._rec_lock = threading.Lock()
        self._timer_thread = None

    # ── Screenshot ───────────────────────────────────────────────────────────

    def take_screenshot(self, value: str = ""):
        """Capture a screenshot in a background thread."""
        threading.Thread(
            target=self._screenshot_worker, args=(value,),
            daemon=True, name="ScreenshotWorker"
        ).start()

    def _screenshot_worker(self, value: str):
        try:
            from PIL import ImageGrab

            opts = self._parse_value(value)
            mode = opts.get("mode", "fullscreen")
            copy_clip = opts.get("clipboard", "true") == "true"
            save_disk = opts.get("save", "true") == "true"
            play_sound = opts.get("sound", "true") == "true"
            open_after = opts.get("open", "false") == "true"

            if mode == "active_window":
                img = self._capture_active_window()
            elif mode == "primary":
                bbox = self._get_primary_bbox()
                img = ImageGrab.grab(bbox=bbox)
            else:
                img = ImageGrab.grab(all_screens=True)

            if img is None:
                print("[Screenshot] Capture failed.")
                self._toast("❌ Capture failed", 2.0)
                return

            # Trigger visual flash & sound effect immediately after pixel grab
            if self.flash_overlay:
                self.flash_overlay.trigger_flash()

            if play_sound:
                self._play_sound()
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"screenshot_{timestamp}.png"
            saved_path = None

            if save_disk:
                save_dir = self._get_screenshot_dir()
                os.makedirs(save_dir, exist_ok=True)
                saved_path = os.path.join(save_dir, filename)
                img.save(saved_path, "PNG")
                print(f"[Screenshot] Saved to {saved_path}")

            if copy_clip:
                self._copy_image_to_clipboard(img)
                print("[Screenshot] Copied to clipboard")

            msg = "📸 Screenshot saved!" if save_disk else "📸 Copied to clipboard!"
            self._toast(msg, 2.0)

            if open_after and saved_path:
                os.startfile(saved_path)

        except Exception as e:
            print(f"[Screenshot] Error: {e}")
            self._toast("❌ Screenshot error", 2.0)

    def _capture_active_window(self):
        """Capture the currently focused window."""
        try:
            from PIL import ImageGrab
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            rect = ctypes.wintypes.RECT()
            ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
            return ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom))
        except Exception as e:
            print(f"[Screenshot] Active window failed: {e}, fallback to fullscreen")
            from PIL import ImageGrab
            return ImageGrab.grab(all_screens=True)

    def _get_primary_bbox(self):
        user32 = ctypes.windll.user32
        return (0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1))

    def _copy_image_to_clipboard(self, img):
        """Copy a PIL Image to the Windows clipboard as DIB bitmap."""
        try:
            import win32clipboard
            import io
            output = io.BytesIO()
            img.convert("RGB").save(output, "BMP")
            data = output.getvalue()[14:]  # Strip 14-byte BMP file header
            output.close()
            CF_DIB = 8
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(CF_DIB, data)
            win32clipboard.CloseClipboard()
        except Exception as e:
            print(f"[Screenshot] Clipboard copy failed: {e}")

    def _play_sound(self):
        try:
            import winsound
            from config import get_resource_path
            shutter_wav = get_resource_path(os.path.join("assets", "shutter.wav"))
            if os.path.exists(shutter_wav):
                winsound.PlaySound(shutter_wav, winsound.SND_FILENAME | winsound.SND_ASYNC)
            else:
                winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
        except Exception as e:
            print(f"[Screenshot] Sound error: {e}")

    # ── Screen Recording ─────────────────────────────────────────────────────

    def toggle_recording(self, value: str = ""):
        """Toggle recording on/off. Called on each key press."""
        with self._rec_lock:
            if self._rec_state == self.IDLE:
                self._start_recording(value)
            elif self._rec_state == self.RECORDING:
                self._stop_recording_signal()

    def _start_recording(self, value: str):
        opts = self._parse_value(value)
        mode = opts.get("mode", "fullscreen")
        fps = int(opts.get("fps", "30"))

        self._rec_state = self.RECORDING
        self._stop_rec.clear()
        self._stop_timer.clear()
        self._rec_start_time = time.time()

        if self.overlay:
            self.overlay.set_message("⏺ REC  00:00")
            self.overlay.show_recording()

        self._timer_thread = threading.Thread(
            target=self._timer_loop, daemon=True, name="RecTimer")
        self._timer_thread.start()

        self._rec_thread = threading.Thread(
            target=self._recording_loop, args=(mode, fps),
            daemon=True, name="ScreenRecWorker")
        self._rec_thread.start()

        self._play_sound()
        print(f"[ScreenRec] Recording started (mode={mode}, fps={fps})")

    def _stop_recording_signal(self):
        self._rec_state = self.FINALIZING
        self._stop_rec.set()
        self._stop_timer.set()
        if self.overlay:
            self.overlay.set_message("⏳ Saving recording…")
        print("[ScreenRec] Stopping…")

    def force_stop(self):
        """Force stop any active recording (used during app shutdown)."""
        with self._rec_lock:
            if self._rec_state == self.RECORDING:
                self._stop_recording_signal()
                if self._rec_thread:
                    self._rec_thread.join(timeout=5.0)

    def _timer_loop(self):
        while not self._stop_timer.is_set():
            if self._rec_start_time and self.overlay:
                elapsed = time.time() - self._rec_start_time
                self.overlay.set_message(f"⏺ REC  {int(elapsed)//60:02d}:{int(elapsed)%60:02d}")
            self._stop_timer.wait(1.0)

    def _recording_loop(self, mode: str, fps: int):
        try:
            from PIL import ImageGrab
            import cv2
            import numpy as np

            if mode == "active_window":
                bbox = self._get_active_window_bbox()
            elif mode == "primary":
                bbox = self._get_primary_bbox()
            else:
                bbox = None

            test = ImageGrab.grab(bbox=bbox, all_screens=(bbox is None))
            width, height = test.size

            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            save_dir = self._get_recording_dir()
            os.makedirs(save_dir, exist_ok=True)
            output_path = os.path.join(save_dir, f"recording_{timestamp}.mp4")

            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

            if not writer.isOpened():
                print("[ScreenRec] Failed to open video writer!")
                with self._rec_lock:
                    self._rec_state = self.IDLE
                self._toast("❌ Recording failed", 2.0)
                return

            frame_interval = 1.0 / fps
            frame_count = 0
            print(f"[ScreenRec] Writing {width}x{height} @ {fps}fps → {output_path}")

            while not self._stop_rec.is_set():
                t0 = time.time()
                frame = ImageGrab.grab(bbox=bbox, all_screens=(bbox is None))
                frame_bgr = cv2.cvtColor(np.array(frame), cv2.COLOR_RGB2BGR)
                writer.write(frame_bgr)
                frame_count += 1
                sleep = frame_interval - (time.time() - t0)
                if sleep > 0:
                    time.sleep(sleep)

            writer.release()
            duration = time.time() - self._rec_start_time
            print(f"[ScreenRec] Saved {frame_count} frames ({duration:.1f}s)")

            self._toast(f"✅ Recording saved! ({int(duration)}s)", 3.0)
            self._play_sound()

        except Exception as e:
            print(f"[ScreenRec] Error: {e}")
            self._toast("❌ Recording error", 2.0)
        finally:
            with self._rec_lock:
                self._rec_state = self.IDLE
                self._rec_start_time = None

    def _get_active_window_bbox(self):
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            rect = ctypes.wintypes.RECT()
            ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
            return (rect.left, rect.top, rect.right, rect.bottom)
        except:
            return None

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _toast(self, msg: str, duration: float):
        if self.overlay:
            self.overlay.set_message(msg)
            self.overlay.show_recording()
            threading.Timer(duration, self.overlay.hide).start()

    def _parse_value(self, value: str) -> dict:
        opts = {}
        if not value:
            return opts
        for part in value.split("|"):
            if "=" in part:
                k, v = part.split("=", 1)
                opts[k.strip()] = v.strip()
            else:
                opts["mode"] = part.strip()
        return opts

    def _get_screenshot_dir(self) -> str:
        if self.config:
            d = self.config.data.get("capture_settings", {}).get("screenshot_dir")
            if d:
                return d
        return DEFAULT_SCREENSHOT_DIR

    def _get_recording_dir(self) -> str:
        if self.config:
            d = self.config.data.get("capture_settings", {}).get("recording_dir")
            if d:
                return d
        return DEFAULT_RECORDING_DIR

    @property
    def is_recording(self) -> bool:
        return self._rec_state == self.RECORDING
