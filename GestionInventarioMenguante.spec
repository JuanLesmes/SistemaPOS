# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

a = Analysis(
    ['run.py'],
    pathex=[os.getcwd()],  # ¡Importante para encontrar 'datcutil'!
    binaries=[],
    datas=[
        (r'venv\Lib\site-packages\escpos\**\*.*', 'escpos'),
        ('images', 'images'),
        *collect_data_files('escpos', include_py_files=True)  # Incluye archivos .py
    ],
    hiddenimports=[
        'escpos.capabilities',
        'escpos.escpos',
        'escpos.constants',
        'escpos.profiles',
        'escpos.printer',  # Necesario para Usb
        'escpos.printer.Usb',
        
        # Otras dependencias
        'usb.backend.libusb1',
        'psycopg2',
        'datcutil',
        
        # Submódulos automáticos (debe ir al final)
        *collect_submodules('escpos')
    ],
    hookspath=['hooks'],
    hooksconfig={},
    runtime_hooks=['runtime-hook-escpos.py'],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='GestionInventarioMenguante',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None
)