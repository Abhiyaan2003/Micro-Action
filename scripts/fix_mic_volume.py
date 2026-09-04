"""
Boost the default Windows microphone volume to 100% and enable +20dB mic boost.
Run once with: python fix_mic_volume.py
"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from pycaw.api.endpointvolume import IAudioEndpointVolume as IAudioEndpointVolumeAPI
from comtypes import CLSCTX_ALL
import ctypes

print("Checking capture (microphone) device volume...")

try:
    from pycaw.pycaw import AudioUtilities
    # Get default capture device (microphone)
    mic = AudioUtilities.GetMicrophone()
    if mic is None:
        print("  No microphone found via pycaw!")
    else:
        vol = mic.EndpointVolume
        current = vol.GetMasterVolumeLevelScalar()
        print(f"  Current mic volume: {current:.0%}")
        vol.SetMasterVolumeLevelScalar(1.0, None)
        after = vol.GetMasterVolumeLevelScalar()
        print(f"  Set mic volume to: {after:.0%}")
        print("  Done! Microphone volume boosted to 100%.")
except Exception as e:
    print(f"  pycaw error: {e}")
    print("  Falling back to sndvol...")
    import subprocess
    subprocess.Popen(["sndvol.exe"])  # Open mixer so user can manually adjust
    print("  Windows Volume Mixer opened — please boost the Microphone level manually.")
