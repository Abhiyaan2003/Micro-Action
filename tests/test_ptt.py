"""
PTT Diagnostic Script
Tests each layer of the speech pipeline independently.
Run with: python test_ptt.py
"""
import sys
import os
import time
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

print("=" * 50)
print("  PTT DIAGNOSTIC TOOL")
print("=" * 50)

# ── STEP 1: PyAudio / Mic ────────────────────────────────
print("\n[1/4] Checking microphone...")
try:
    import pyaudio
    pa = pyaudio.PyAudio()
    mic_count = pa.get_device_count()
    input_devices = []
    for i in range(mic_count):
        d = pa.get_device_info_by_index(i)
        if d["maxInputChannels"] > 0:
            input_devices.append((i, d["name"]))

    if not input_devices:
        print("  FAIL: No input microphone devices found!")
        sys.exit(1)
    
    print(f"  OK — Found {len(input_devices)} input device(s):")
    for idx, name in input_devices:
        print(f"       [{idx}] {name}")

    default_input = pa.get_default_input_device_info()
    print(f"  Default mic: {default_input['name']}")
    pa.terminate()
except Exception as e:
    print(f"  FAIL: PyAudio error — {e}")
    sys.exit(1)

# ── STEP 2: Record 2 seconds of audio ───────────────────
print("\n[2/4] Recording 4 seconds of audio...")
print("      >>> SPEAK NOW! Say something like 'hello world' <<<")
SAMPLE_RATE = 16000
CHUNK = 512
try:
    pa = pyaudio.PyAudio()
    stream = pa.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    frames = []
    total_chunks = int(SAMPLE_RATE / CHUNK * 4)   # 4 seconds
    for _ in range(total_chunks):
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)
    stream.stop_stream()
    stream.close()
    pa.terminate()

    audio_np = np.frombuffer(b"".join(frames), dtype=np.int16)
    rms = np.sqrt(np.mean(audio_np.astype(np.float32) ** 2))
    peak = np.abs(audio_np).max()
    print(f"  OK — {len(audio_np)} samples captured | RMS={rms:.1f} | Peak={peak}")

    if rms < 50:
        print("  WARNING: Audio is very quiet — check mic volume or speak louder")
    else:
        print("  Audio level looks good!")

except Exception as e:
    print(f"  FAIL: Recording error — {e}")
    sys.exit(1)

# ── STEP 3: Load Whisper ─────────────────────────────────
print("\n[3/4] Loading Whisper model (tiny — fastest)...")
try:
    from faster_whisper import WhisperModel
    t0 = time.time()
    model = WhisperModel("tiny", device="cpu", compute_type="int8")
    elapsed = time.time() - t0
    print(f"  OK — Model loaded in {elapsed:.1f}s")
except Exception as e:
    print(f"  FAIL: Whisper load error — {e}")
    sys.exit(1)

# ── STEP 4: Transcribe the recorded audio ────────────────
print("\n[4/4] Transcribing recorded audio...")
print(f"  Audio RMS={rms:.1f} (threshold=5) — {'will transcribe' if rms >= 5 else 'SKIPPED (too quiet)'}")
try:
    audio_f32 = audio_np.astype(np.float32) / 32768.0
    segments, info = model.transcribe(
        audio_f32,
        language="en",
        vad_filter=False,          # Disabled so quiet mics still get transcribed
        beam_size=5,
        best_of=5,
        temperature=0.0,
        condition_on_previous_text=False,
    )
    text = " ".join(seg.text.strip() for seg in segments).strip()
    if text:
        print(f"  OK — Transcribed: \"{text}\"")
    else:
        print("  WARNING: Transcription returned empty string.")
        print("           Your mic may be too quiet - try boosting it in Windows Sound Settings.")
        print("           Right-click speaker icon -> Sound settings -> Input -> Microphone -> Volume")
except Exception as e:
    print(f"  FAIL: Transcription error — {e}")
    sys.exit(1)

print("\n" + "=" * 50)
print("  ALL STEPS PASSED")
print("=" * 50)
