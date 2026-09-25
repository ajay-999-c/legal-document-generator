# Windows-only, one-file, windowed distribution. No project-directory globbing.
from pathlib import Path
import sys
import yaml
from PyInstaller.utils.hooks import collect_data_files

if sys.platform != 'win32':
    raise SystemExit('Build the Windows executable on Windows.')

root = Path(SPECPATH)
sys.path.insert(0, str(root))
from document_registry import SPECS
from runtime_paths import UNCONFIGURED_SPREADSHEET_ID

# Only the reviewed seed and its six named production templates are assets.
# Never glob the checkout or bundle office configuration/credentials.
seed_path = root / 'config.example.yaml'
seed = yaml.safe_load(seed_path.read_text(encoding='utf-8'))
if seed['google']['spreadsheet_id'] != UNCONFIGURED_SPREADSHEET_ID or seed['google']['credentials_file'] != 'credentials.json':
    raise SystemExit('Build requires the redacted configuration seed.')
if set(seed['documents']) != set(SPECS) or not all(d['enabled'] for d in seed['documents'].values()):
    raise SystemExit('Seed must enable all six registry documents.')
templates = [root / seed['documents'][key]['template_path'] for key in SPECS]
if any(not path.is_file() or path.parent != root / 'templates' or path.suffix != '.docx' for path in templates):
    raise SystemExit('A production template is missing or outside templates/.')
datas = [(str(path), 'templates') for path in templates]
datas += [(str(seed_path), '.')]
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
