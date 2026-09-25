"""Desktop runtime locations, separate from read-only packaged resources."""
import ctypes
import os
from pathlib import Path
import sys

APP_ID = 'LegalDocumentGenerator'
UNCONFIGURED_SPREADSHEET_ID = 'UNCONFIGURED_LEGAL_DOCUMENT_GENERATOR'
SOURCE_ROOT = Path(__file__).resolve().parent


def is_windows():
    return sys.platform == 'win32'


def is_frozen():
    return bool(getattr(sys, 'frozen', False))


def resource_root():
    return Path(getattr(sys, '_MEIPASS', SOURCE_ROOT))


def data_directory():
    if is_windows():
        return Path(os.environ.get('APPDATA', str(Path.home() / 'AppData' / 'Roaming'))) / APP_ID
    if is_frozen():
        return Path.home() / 'Library' / 'Application Support' / APP_ID if sys.platform == 'darwin' else Path.home() / '.local' / 'share' / APP_ID
    return SOURCE_ROOT


def config_path():
    # Windows source and packaged GUI share one per-user configuration. CLI paths
    # are owned by config_manager and remain unchanged.
    return (data_directory() if is_windows() or is_frozen() else SOURCE_ROOT) / 'config.yaml'


def documents_directory():
    if is_windows():
        # CSIDL_PERSONAL resolves redirected Documents (including OneDrive).
        buffer = ctypes.create_unicode_buffer(32768)
        if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buffer) == 0 and buffer.value:
            return Path(buffer.value)
    return Path.home() / 'Documents'


def default_output(key, label):
    # Labels are administrator metadata; never allow one to become a path.
    safe = ''.join(c for c in label if c.isalnum() or c in ' -_').strip(' .')
    return documents_directory() / f'{safe or key} Documents'


def desktop_log_path(settings=None):
    if is_windows() or is_frozen():
        # Installed logs cannot escape AppData, even with a legacy absolute path.
        name = settings.log_file.name if settings is not None else 'generator.log'
        return data_directory() / 'logs' / name
    return settings.log_file if settings is not None else data_directory() / 'logs' / 'generator.log'
