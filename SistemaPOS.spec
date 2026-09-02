# -*- mode: python ; coding: utf-8 -*-
# Empaquetado con PyInstaller. Desde la raíz del proyecto, con el venv activo:
#     pyinstaller SistemaPOS.spec
# El ejecutable queda en dist/SistemaPOS.exe. Junto a él deben ir .env y config.json
# (se copian las plantillas .env.example y config.example.json al primer arranque).

a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=[("libusb-1.0.dll", ".")],
    datas=[
        ("images", "images"),
        ("migrations", "migrations"),
        ("config.example.json", "."),
        (".env.example", "."),
    ],
    hiddenimports=["usb.backend.libusb1"],
    hookspath=["hooks"],
    hooksconfig={},
    runtime_hooks=["runtime-hook-escpos.py"],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="SistemaPOS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
