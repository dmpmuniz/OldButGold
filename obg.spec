# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

_tool_dir = Path(os.getcwd()) / "tools"
_tool_datas = []
if _tool_dir.is_dir():
    for f in _tool_dir.iterdir():
        if f.is_file() and not f.name.startswith("."):
            _tool_datas.append((str(f), "tools"))

a = Analysis(
    ['obg/__main__.py'],
    pathex=[os.getcwd()],
    binaries=[],
    datas=collect_data_files('rich._unicode_data') + _tool_datas,
    hiddenimports=collect_submodules('rich._unicode_data'),
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
    name='OldButGold',
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
    entitlements_file=None,
)
