# build/pyinstaller.spec
from PyInstaller.utils.hooks import collect_submodules
block_cipher = None

hiddenimports = collect_submodules('core') + collect_submodules('plugins')

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('ui/dist', 'ui/dist'),
        ('schemas', 'schemas'),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    excludes=[
        # LOW-RISK ONLY (nach Exercise bestätigt)
        'tkinter', 'tcl', 'pydoc', 'test', 'unittest'
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    name='sheratan_core',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # konservativ
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='sheratan_core',
)
