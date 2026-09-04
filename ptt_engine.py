"""
PTT Engine — manages microphone audio capture, live partial transcription preview
with LocalAgreement stabilization, and final accuracy pass on release.

Feature Highlights:
1. Live Transcription: Periodically re-transcribes accumulated buffer using fast beam_size=1 pass.
   Compares consecutive hypotheses (LocalAgreement policy). Words matching across two ticks
   become 'committed' and are typed incrementally into the active window. Uncommitted words
   are rendered as 'tentative' in the visual overlay.
"""
import threading
import time
import numpy as np
import pyaudio

SAMPLE_RATE  = 16000
CHUNK_FRAMES = 1024        # 64ms per chunk
MIN_RMS      = 5           # ignore truly silent recordings (unplugged mic)
WHISPER_MODEL_NAME = "base"


class PTTEngine:
    def __init__(self, config=None, overlay=None):
        self.config          = config
        self.overlay         = overlay
        self.model           = None
        self._model_lock     = threading.Lock()
        self.model_loaded    = False
        self.model_loading   = False
        self._unload_timer   = None

        self._recording      = False
        self._audio_buf      = []           # list of np.int16 chunks
        self._mic_thread     = None
        self._tick_thread    = None
        self._stop_mic       = threading.Event()
        self._stop_tick      = threading.Event()
        self.last_transcription = ""

        # Live transcription state per session
        self._committed_words = []
        self._prev_hypothesis_words = None

        # Pre-load model in background on startup only if PTT is mapped
        has_ptt = False
        if self.config:
            for act in self.config.data.get("keys", {}).values():
                if isinstance(act, dict) and act.get("type") == "ptt":
                    has_ptt = True
                    break

        if has_ptt:
            self._load_model()

    # ── Model loading ────────────────────────────────────────────────────────

    def preload(self):
        """Preload the single Whisper engine model if not already loaded or loading."""
        with self._model_lock:
            if not self.model_loaded and not self.model_loading:
                self._load_model()

    def _load_model(self):
        """Load Whisper engine model in a daemon thread."""
        if self.model_loading:
            return
        self.model_loading = True
        self.model_loaded  = False

        if self.overlay:
            self.overlay.set_message(f"⏳ Loading Whisper Engine…")
            self.overlay.show_recording()

        def _task():
            try:
                print(f"[PTT] Loading Whisper '{WHISPER_MODEL_NAME}' engine…")
                from faster_whisper import WhisperModel
                m = WhisperModel(WHISPER_MODEL_NAME, device="cpu", compute_type="int8")
                with self._model_lock:
                    self.model        = m
                    self.model_loaded = True
                print(f"[PTT] Whisper engine ready.")
                self._reset_inactivity_timer()
            except Exception as e:
                print(f"[PTT] Model load error: {e}")
            finally:
                self.model_loading = False
                if self.overlay:
                    self.overlay.hide()

        threading.Thread(target=_task, daemon=True).start()

    # ── Public API ───────────────────────────────────────────────────────────

    def start(self):
        """Called when PTT key is pressed down."""
        # Cancel any active unload timer
        with self._model_lock:
            if self._unload_timer is not None:
                self._unload_timer.cancel()
                self._unload_timer = None

        # Trigger load if model is not loaded yet
        if not self.model_loaded and not self.model_loading:
            self._load_model()

        if self._recording:
            return

        self._recording = True
        self._audio_buf = []

        self._committed_words = []
        self._prev_hypothesis_words = None

        self._stop_mic.clear()
        self._stop_tick.clear()

        if self.overlay:
            if not self.model_loaded:
                self.overlay.set_message("⏳ Loading & Recording…")
            else:
                self.overlay.set_message("🎙️ Recording…")
            self.overlay.show_recording()

        self._mic_thread = threading.Thread(
            target=self._mic_loop, daemon=True, name="PTTMic"
        )
        self._mic_thread.start()

        self._tick_thread = threading.Thread(
            target=self._tick_loop, daemon=True, name="PTTTick"
        )
        self._tick_thread.start()
        print(f"[PTT] Recording started (model={WHISPER_MODEL_NAME}).")

    def stop(self):
        """Called when PTT key is released — transcribes full buffer and reconciles."""
        if not self._recording:
            if self.overlay:
                self.overlay.hide()
            return

        self._recording = False
        self._stop_mic.set()
        self._stop_tick.set()

        # Wait for mic and tick threads to finish
        if self._mic_thread:
            self._mic_thread.join(timeout=1.5)
        if self._tick_thread:
            self._tick_thread.join(timeout=1.5)

        if self.overlay:
            if self.model_loading:
                self.overlay.set_message("⏳ Waiting for model…")
            else:
                self.overlay.set_message("✨ Transcribing…")

        audio_snapshot = self._audio_buf[:]
        self._audio_buf = []

        committed_snap = self._committed_words[:]

        threading.Thread(
            target=self._transcribe_and_type,
            args=(audio_snapshot, committed_snap),
            daemon=True,
            name="PTTTranscribe"
        ).start()

    def _reset_inactivity_timer(self):
        with self._model_lock:
            if self._unload_timer is not None:
                self._unload_timer.cancel()
                self._unload_timer = None
            
            # Start a new timer for 60 seconds
            self._unload_timer = threading.Timer(60.0, self._unload_model)
            self._unload_timer.daemon = True
            self._unload_timer.start()

    def _unload_model(self):
        with self._model_lock:
            if self.model is not None:
                print("[PTT] Whisper model inactive for 60s. Unloading model to save RAM...")
                self.model = None
                self.model_loaded = False
                self._unload_timer = None
                import gc
                gc.collect()

    # ── Mic recording loop ───────────────────────────────────────────────────

    def _mic_loop(self):
        pa = pyaudio.PyAudio()
        stream = None
        try:
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK_FRAMES,
            )
            while not self._stop_mic.is_set():
                raw = stream.read(CHUNK_FRAMES, exception_on_overflow=False)
                self._audio_buf.append(np.frombuffer(raw, dtype=np.int16))
        except Exception as e:
            print(f"[PTT Mic] Error: {e}")
            if self.overlay:
                self.overlay.set_message("❌ Mic Error")
                threading.Timer(1.5, self.overlay.hide).start()
        finally:
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            pa.terminate()

    # ── Live Transcription Loop ──────────────────────────────────────────────

    def _tick_loop(self):
        """
        Runs every ~1.0s while recording. Re-transcribes the accumulated audio buffer
        with beam_size=1, stabilizes via LocalAgreement, and types committed deltas.
        """
        TICK_INTERVAL = 1.0
        MIN_SAMPLES = int(0.5 * SAMPLE_RATE)  # Skip ticks for <0.5s audio

        while not self._stop_tick.is_set():
            if self._stop_tick.wait(timeout=TICK_INTERVAL):
                break

            if not self._recording:
                break

            chunks_snap = self._audio_buf[:]
            if not chunks_snap:
                continue

            audio_np = np.concatenate(chunks_snap).astype(np.float32) / 32768.0
            if len(audio_np) < MIN_SAMPLES:
                continue

            rms = float(np.sqrt(np.mean(audio_np ** 2)) * 32768)
            if rms < MIN_RMS:
                continue

            with self._model_lock:
                model = self.model
                loaded = self.model_loaded
            if model is None or not loaded:
                continue

            try:
                segments, info = model.transcribe(
                    audio_np,
                    language=None,  # always auto-detect
                    beam_size=1,
                    best_of=1,
                    temperature=0.0,
                    vad_filter=True,
                    condition_on_previous_text=False
                )

                text = " ".join(seg.text.strip() for seg in segments).strip()
                if not text:
                    continue

                curr_words = text.split()
                n_committed = len(self._committed_words)
                newly_committed = []

                if self._prev_hypothesis_words is not None:
                    prev_uncommitted = self._prev_hypothesis_words[n_committed:]
                    curr_uncommitted = curr_words[n_committed:]

                    match_count = 0
                    min_len = min(len(prev_uncommitted), len(curr_uncommitted))
                    for i in range(min_len):
                        if prev_uncommitted[i] == curr_uncommitted[i]:
                            match_count += 1
                        else:
                            break

                    if match_count > 0:
                        newly_committed = curr_uncommitted[:match_count]
                        self._committed_words.extend(newly_committed)

                self._prev_hypothesis_words = curr_words

                if newly_committed:
                    delta_text = " ".join(newly_committed)
                    if n_committed > 0:
                        delta_text = " " + delta_text
                    print(f"[PTT Live] Committed delta: '{delta_text}'")
                    _paste_text(delta_text)

                n_committed_updated = len(self._committed_words)
                tentative_words = curr_words[n_committed_updated:]

                committed_str = " ".join(self._committed_words)
                tentative_str = " ".join(tentative_words)

                if self.overlay and self._recording:
                    self.overlay.set_partial(committed_str, tentative_str)

            except Exception as e:
                print(f"[PTT Live] Tick error: {e}")

    # ── Final Release Transcription ─────────────────────────────────────────

    def _transcribe_and_type(self, chunks: list, committed_words: list):
        try:
            if not chunks:
                return

            audio_np = np.concatenate(chunks).astype(np.float32) / 32768.0
            if len(audio_np) < int(0.5 * SAMPLE_RATE):
                print("[PTT] Audio buffer < 0.5s — skipping.")
                return

            rms = float(np.sqrt(np.mean(audio_np ** 2)) * 32768)
            if rms < MIN_RMS:
                print(f"[PTT] Audio too quiet (RMS={rms:.1f}) — skipping.")
                return

            print(f"[PTT] Final pass on {len(audio_np)/SAMPLE_RATE:.1f}s audio (RMS={rms:.0f})…")

            start_wait = time.time()
            while self.model_loading and (time.time() - start_wait < 30.0):
                time.sleep(0.1)

            with self._model_lock:
                model = self.model
            if model is None:
                print("[PTT] Model not available — skipping transcription.")
                return

            segments, info = model.transcribe(
                audio_np,
                language=None,               # always auto-detect on final pass
                vad_filter=False,            # disabled for full buffer accuracy
                beam_size=5,
                best_of=5,
                temperature=0.0,             # greedy — fast and consistent
                condition_on_previous_text=False,
                word_timestamps=False,
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()

            if not text:
                print("[PTT] Empty final transcription — nothing typed.")
                return

            print(f"[PTT] Final raw result: \"{text}\"")

            final_words = text.split()
            n_committed = len(committed_words)

            if n_committed > 0:
                if len(final_words) >= n_committed and final_words[:n_committed] == committed_words:
                    remaining_words = final_words[n_committed:]
                else:
                    if len(final_words) > n_committed:
                        remaining_words = final_words[n_committed:]
                    else:
                        remaining_words = []
            else:
                remaining_words = final_words

            full_text_list = committed_words + remaining_words
            full_text = " ".join(full_text_list).strip()

            if remaining_words:
                delta_text = " ".join(remaining_words)
                if n_committed > 0:
                    delta_text = " " + delta_text
                print(f"[PTT] Typing final delta: \"{delta_text}\"")
                _paste_text(delta_text)
            else:
                print("[PTT] All words were already committed and typed during recording.")

            self.last_transcription = full_text
            if self.overlay and full_text:
                self.overlay.set_partial(full_text, "")

        except Exception as e:
            print(f"[PTT] Transcription error: {e}")
        finally:
            if self.overlay:
                time.sleep(0.3)
                self.overlay.hide()
            self._reset_inactivity_timer()

    @property
    def _running(self):
        return self._recording

    @property
    def _typed_so_far(self):
        return self.last_transcription


# ── Helpers ──────────────────────────────────────────────────────────────────

def _paste_text(text: str):
    """
    Paste text at cursor using clipboard, with backup and restore.
    Uses Ctrl+V for compatibility with all apps (including non-English ones).
    """
    import win32clipboard
    import win32con
    import pyautogui

    # 1. Backup existing clipboard
    old_text = None
    try:
        win32clipboard.OpenClipboard()
        if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
            old_text = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
    except Exception:
        pass

    # 2. Write transcribed text and paste
    for _ in range(5):
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
            win32clipboard.CloseClipboard()
            break
        except Exception:
            time.sleep(0.015)
    else:
        print("[PTT Clipboard] Could not write to clipboard — skipping paste.")
        return

    pyautogui.hotkey("ctrl", "v")
    print(f"[PTT] Pasted {len(text)} chars.")

    # 3. Restore clipboard in background after paste completes
    if old_text is not None:
        def _restore():
            time.sleep(0.25)
            for _ in range(5):
                try:
                    win32clipboard.OpenClipboard()
                    win32clipboard.EmptyClipboard()
                    win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, old_text)
                    win32clipboard.CloseClipboard()
                    return
                except Exception:
                    time.sleep(0.015)
        threading.Thread(target=_restore, daemon=True).start()

