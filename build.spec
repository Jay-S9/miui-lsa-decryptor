# build.spec — PyInstaller configuration for LSA Decryptor
# Produces a single .exe with no external dependencies
# Run: pyinstaller build.spec

import os
import sys
from pathlib import Path

# ── Locate customtkinter data files ─────────────────────────────────────────
# CustomTkinter ships theme JSON files and assets that must be bundled
import customtkinter
CTK_PATH = Path(customtkinter.__file__).parent

block_cipher = None

a = Analysis(
    ['src/gui.py'],                         # Entry point
    pathex=['.'],                           # Project root on sys.path
    binaries=[],
    datas=[
        # Bundle the entire customtkinter package (themes, assets, images)
        (str(CTK_PATH), 'customtkinter'),
    ],
    hiddenimports=[
        'customtkinter',
        'Crypto',
        'Crypto.Cipher',
        'Crypto.Cipher.AES',
        'Crypto.Util',
        'tkinter',
        'tkinter.filedialog',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Trim unused heavy packages from the bundle
        'matplotlib', 'numpy', 'PIL', 'scipy',
        'pandas', 'pytest', 'IPython',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='LSA-Decryptor',           # Output filename: LSA-Decryptor.exe
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,                       # Compress with UPX if available (smaller file)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,                  # No black terminal window — GUI only
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='assets/icon.ico',       # Uncomment once you have an icon file
)
