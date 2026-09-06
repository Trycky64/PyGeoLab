# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification for PyGeoLab desktop releases."""

from pathlib import Path

from PyInstaller.compat import is_win

root = Path(SPECPATH).parent
icon = root / "assets" / ("pygeolab.ico" if is_win else "pygeolab.png")
version_file = root / "packaging" / "version_info.txt"

a = Analysis(
    [str(root / "src" / "pygeolab" / "__main__.py")],
    pathex=[str(root / "src")],
    binaries=[],
    datas=[(str(root / "src" / "pygeolab" / "resources" / "icon.svg"), "pygeolab/resources")],
    hiddenimports=["PySide6.QtSvg"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PyGeoLab",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(icon),
    version=str(version_file) if is_win else None,
)
coll = COLLECT(a.binaries, a.datas, exe, name="PyGeoLab")
