# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Specification for IRIS Virtual Assistant
Packages IRIS into a standalone Windows desktop executable with no console window.
"""

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None
base_dir = Path(__file__).resolve().parent

datas = [
    (str(base_dir / "iris" / "database" / "schema.py"), "iris/database"),
]

hiddenimports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "win32gui",
    "win32con",
    "win32api",
    "win32clipboard",
    "pywinauto",
    "pyttsx3",
    "edge_tts",
    "pygame",
    "speech_recognition",
    "sqlite3",
    "psutil",
    "requests",
    "dotenv",
]

hiddenimports += collect_submodules("iris")

a = Analysis(
    ["iris/main.py"],
    pathex=[str(base_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="IRIS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Silent desktop application without black command prompt window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="IRIS",
)
