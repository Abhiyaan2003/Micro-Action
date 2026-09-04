import wave
import struct
import random
import math
import os

def create_shutter_sound(filename=None):
    if filename is None:
        filename = os.path.join(os.path.dirname(__file__), "..", "assets", "shutter.wav")
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    sample_rate = 44100
    
    samples = []
    
    # Phase 1: Mechanical mirror/shutter click (0 to 18ms)
    t1 = 0.018
    n1 = int(sample_rate * t1)
    for i in range(n1):
        t = i / sample_rate
        env = math.exp(-t * 220)
        noise = (random.random() * 2 - 1)
        tone = math.sin(2 * math.pi * 1400 * t) * 0.4
        val = int((noise * 0.7 + tone * 0.3) * env * 32000)
        samples.append(val)

    # Phase 2: Short mechanical delay (12ms)
    t_gap = 0.012
    n_gap = int(sample_rate * t_gap)
    for _ in range(n_gap):
        samples.append(0)

    # Phase 3: Shutter release curtain snap (0 to 25ms)
    t2 = 0.025
    n2 = int(sample_rate * t2)
    for i in range(n2):
        t = i / sample_rate
        env = math.exp(-t * 180)
        noise = (random.random() * 2 - 1)
        tone = math.sin(2 * math.pi * 900 * t) * 0.3
        val = int((noise * 0.65 + tone * 0.35) * env * 28000)
        samples.append(val)

    with wave.open(filename, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        for s in samples:
            f.writeframes(struct.pack('<h', max(-32768, min(32767, s))))

if __name__ == "__main__":
    create_shutter_sound()
    print("Camera shutter sound created successfully.")
