# -*- mode: python ; coding: utf-8 -*-
import os
import sys

# Obtener ruta de Flet
import flet
flet_path = os.path.dirname(flet.__file__)

# Archivos de datos de Flet que necesitamos incluir
flet_datas = []

# Agregar todos los archivos JSON de flet
for root, dirs, files in os.walk(flet_path):
    for file in files:
        if file.endswith('.json'):
            src = os.path.join(root, file)
            dst = os.path.relpath(root, os.path.dirname(flet_path))
            flet_datas.append((src, dst))

a = Analysis(
    ['app_emisora.py'],
    pathex=[],
    binaries=[],
    datas=flet_datas,
    hiddenimports=[
        'flet',
        'flet_core',
        'flet_runtime',
        'anyio',
        'anyio._backends',
        'anyio._backends._asyncio',
        'httpx',
        'httpcore',
        'h11',
        'certifi',
        'pandas',
        'openpyxl',
        'getmac',
    ],
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
    a.binaries,
    a.datas,
    [],
    name='SoporteTecnico_Emisora',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='NONE',
)
