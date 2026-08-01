# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['open_jarvis\\ui\\arayuz.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('open_jarvis/ui/world_map/world_map.html', 'open_jarvis/ui/world_map'),
        ('open_jarvis/ui/jarvis_os/jarvis_os.html', 'open_jarvis/ui/jarvis_os'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'scipy',
        'sklearn',
        'pandas',
        'tcpdump',
    ],
    noarchive=False,
    optimize=2,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Open.Jarvis',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=True,
    upx=True,
    upx_exclude=[],
    name='Open.Jarvis',
)
