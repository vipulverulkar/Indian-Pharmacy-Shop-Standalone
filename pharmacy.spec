# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = [
    "flask",
    "flask_cors",
    "sqlalchemy",
    "sqlalchemy.dialects.sqlite",
    "werkzeug.security",
    "waitress",
    "migrations",
    "models",
    "app",
]
hiddenimports += collect_submodules("waitress")

a = Analysis(
    ["launcher.py"],
    pathex=["backend"],
    binaries=[],
    datas=[("frontend/dist", "frontend/dist")],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "test", "unittest", "pytest"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="IndianPharmacyShop",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
