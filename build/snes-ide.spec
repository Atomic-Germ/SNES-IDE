# -*- mode: python ; coding: utf-8 -*-
import os
import glob
from pathlib import Path

block_cipher = None

# Helper to collect all files under a directory into datas list as tuples
def collect_dir(src_dir, target_dir):
    src_dir = Path(src_dir)
    datas = []
    if not src_dir.exists():
        return datas
    for f in glob.glob(str(src_dir / '**' / '*'), recursive=True):
        if os.path.isfile(f):
            rel = os.path.relpath(f, src_dir)
            datas.append((f, os.path.join(target_dir, os.path.dirname(rel))))
    return datas

# Collect resources
datas = []
datas += collect_dir('src/tools', 'tools')
datas += collect_dir('libs', 'libs')
datas += collect_dir('assets/icons', 'icons')

# Add top-level useful files
for p in ['README.md', 'LICENSE.txt', 'INSTALL_VARIANT.bat', 'INSTALL_VARIANT.sh', 'INSTALL.sh']:
    if os.path.isfile(p):
        datas.append((p, '.'))

# Analysis
a = Analysis([
    'src/snes-ide.py'
],
    pathex=[os.getcwd()],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='snes-ide',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='snes-ide'
)
