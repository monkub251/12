# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec — one file, no console window, requests Administrator.

    python -m PyInstaller BANNARAKX.spec --noconfirm   ->  dist/BANNARAKX.exe
"""

import os

block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[("assets", "assets")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # PySide6 ships far more than a two-page desktop tool ever touches.
        # Dropping these takes the exe from roughly 90 MB to roughly 45 MB.
        "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebEngineQuick", "PySide6.QtQuick", "PySide6.QtQml",
        "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets",
        "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.QtCharts",
        "PySide6.QtDataVisualization", "PySide6.QtPdf", "PySide6.QtPdfWidgets",
        "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtBluetooth",
        "PySide6.QtPositioning", "PySide6.QtNfc", "PySide6.QtSerialPort",
        "PySide6.QtDesigner", "PySide6.QtHelp", "PySide6.QtQuick3D",
        "PySide6.QtNetworkAuth", "PySide6.QtRemoteObjects",
        "tkinter", "unittest", "pydoc", "doctest", "pdb", "pytest",
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
    name="BANNARAKX",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX on Qt DLLs is the single biggest cause of
                        # false-positive AV flags. Size is not worth that.
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,     # every tweak writes HKLM or controls a service
    icon=os.path.join("assets", "logo.ico")
         if os.path.exists(os.path.join("assets", "logo.ico")) else None,
)
