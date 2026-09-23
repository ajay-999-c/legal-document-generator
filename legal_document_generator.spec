# Windows-only, one-file, windowed distribution. No project-directory globbing.
from pathlib import Path
import sys
from PyInstaller.utils.hooks import collect_data_files

if sys.platform != 'win32':
    raise SystemExit('Build the Windows executable on Windows.')

root = Path(SPECPATH)
templates = sorted((root / 'templates').glob('*.docx'))
if not templates:
    raise SystemExit('No document templates found.')
datas = [(str(path), 'templates') for path in templates if not path.name.startswith('~$')]
datas += collect_data_files('docx')

a = Analysis(
    [str(root / 'app.py')],
    pathex=[str(root)], binaries=[], datas=datas,
    hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['pytest', 'tests'], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name='Legal Document Generator', debug=False,
    bootloader_ignore_signals=False, strip=False, upx=False,
    console=False, disable_windowed_traceback=True,
)
