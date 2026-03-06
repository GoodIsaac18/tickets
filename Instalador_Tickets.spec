# -*- mode: python ; coding: utf-8 -*-
# =============================================================================
# Instalador_Tickets.spec — PyInstaller spec para el instalador gráfico
# =============================================================================

import os
import sys
from pathlib import Path

# Paths
BASE_DIR = os.path.abspath('.')
PYTHON_EMBED = os.path.join(BASE_DIR, 'python_embed')
SITE_PACKAGES = os.path.join(PYTHON_EMBED, 'Lib', 'site-packages')
FLET_DESKTOP_APP = os.path.join(SITE_PACKAGES, 'flet_desktop', 'app')
FLET_PKG = os.path.join(SITE_PACKAGES, 'flet')
ICONS_DIR = os.path.join(BASE_DIR, 'icons')

a = Analysis(
    ['instalador.py'],
    pathex=[SITE_PACKAGES],
    binaries=[],
    datas=[
        # Bundlear el runtime de Flet Desktop (Flutter engine)
        (FLET_DESKTOP_APP, os.path.join('flet_desktop', 'app')),
        # Bundlear datos del paquete flet (icons.json, cupertino_icons.json)
        (os.path.join(FLET_PKG, 'controls', 'material', 'icons.json'), os.path.join('flet', 'controls', 'material')),
        (os.path.join(FLET_PKG, 'controls', 'cupertino', 'cupertino_icons.json'), os.path.join('flet', 'controls', 'cupertino')),
        # Bundlear los iconos de la app
        (ICONS_DIR, 'icons'),
        # Módulo de actualizaciones desde GitHub (importado dinámicamente)
        (os.path.join(BASE_DIR, 'actualizador_github.py'), '.'),
        # Metadata de versión
        (os.path.join(BASE_DIR, 'version.json'), '.'),
    ],
    hiddenimports=[
        'flet',
        'flet.controls',
        'flet_desktop',
        'flet_desktop.app',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        'pandas', 'openpyxl', 'numpy', 'PIL', 'pillow',
        'matplotlib', 'scipy', 'tkinter', 'unittest',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Instalador_Tickets_IT',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    icon=os.path.join(ICONS_DIR, 'receptora.ico'),
    uac_admin=True,
)
