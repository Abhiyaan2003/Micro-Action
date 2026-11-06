# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_all
import PyQt6

# Collect faster_whisper and ctranslate2 dependencies (datas, binaries, submodules)
whisper_datas, whisper_binaries, whisper_hidden = collect_all('faster_whisper')
ct2_datas, ct2_binaries, ct2_hidden = collect_all('ctranslate2')

# Bundle the exact MSVC C++ runtime DLLs shipped alongside PyQt6 to guarantee
# that Qt6/PyQt6 loads matching procedure entry points without colliding with
# older system-wide msvcp140*.dll versions in C:\Windows\System32.
qt6_bin = Path(PyQt6.__file__).parent / "Qt6" / "bin"
extra_binaries = []
if qt6_bin.exists():
    for pattern in ("*140*.dll", "vccorlib*.dll"):
        for dll in qt6_bin.glob(pattern):
            extra_binaries.append((str(dll), "."))
            extra_binaries.append((str(dll), "PyQt6/Qt6/bin"))

all_datas = [
    ('app_icon.ico', '.'),
    ('assets', 'assets'),
    ('qt.conf', '.'),
] + whisper_datas + ct2_datas

all_binaries = extra_binaries + whisper_binaries + ct2_binaries

all_hiddenimports = [
    'pystray',
    'win32clipboard',
    'PyQt6.sip',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.QtNetwork',
] + whisper_hidden + ct2_hidden

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=all_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MicroAction',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['app_icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='MicroAction',
)
