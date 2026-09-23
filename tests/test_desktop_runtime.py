from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import logging
import runpy
import sys
import types
import pytest
import yaml

import app
import desktop
from desktop_config import DesktopConfig
from models import SetupError
import runtime_paths
from tests.conftest import ROOT


def test_source_paths_independent_of_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(runtime_paths, 'is_frozen', lambda: False)
    assert runtime_paths.config_path() == ROOT / 'config.yaml'
    assert runtime_paths.resource_root() == ROOT


def test_windows_runtime_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime_paths, 'is_windows', lambda: True)
    monkeypatch.setattr(runtime_paths, 'is_frozen', lambda: True)
    monkeypatch.setenv('APPDATA', str(tmp_path / 'Roaming'))
    expected = tmp_path / 'Roaming' / 'LegalDocumentGenerator'
    assert runtime_paths.config_path() == expected / 'config.yaml'
    assert runtime_paths.desktop_log_path() == expected / 'logs' / 'generator.log'
    assert runtime_paths.desktop_log_path(SimpleNamespace(log_file=Path('/legacy/logs/office.log'))) == expected / 'logs' / 'office.log'


def test_windows_redirected_documents(monkeypatch, tmp_path):
    def folder(hwnd, csidl, token, flags, buffer):
        assert csidl == 5
        buffer.value = str(tmp_path / 'Redirected Documents')
        return 0
    monkeypatch.setattr(runtime_paths, 'is_windows', lambda: True)
    monkeypatch.setattr(runtime_paths.ctypes, 'windll', SimpleNamespace(shell32=SimpleNamespace(SHGetFolderPathW=folder)), raising=False)
    assert runtime_paths.default_output('noc', 'NOC') == tmp_path / 'Redirected Documents' / 'NOC Documents'


def test_missing_output_settings_default_and_persist(settings, tmp_path, monkeypatch):
    data = yaml.safe_load(settings.config_path.read_text(encoding='utf-8'))
    data['documents']['noc'].pop('output_dir')
    data['documents']['affidavit']['output_dir'] = ''
    monkeypatch.setattr(runtime_paths, 'documents_directory', lambda: tmp_path / 'Documents')
    settings.config_path.write_text(yaml.safe_dump(data), encoding='utf-8')
    store = DesktopConfig(settings.config_path)
    loaded = store.load()
    assert loaded.documents['noc'].output_dir == tmp_path / 'Documents' / 'noc Documents'
    assert loaded.documents['affidavit'].output_dir == tmp_path / 'Documents' / 'affidavit Documents'
    assert loaded.documents['consent'].output_dir == settings.documents['consent'].output_dir
    persisted = yaml.safe_load(settings.config_path.read_text(encoding='utf-8'))
    assert persisted['documents']['noc']['output_dir'] == str(loaded.documents['noc'].output_dir)
    before = settings.config_path.read_bytes()
    assert store.load() == loaded
    assert settings.config_path.read_bytes() == before


def test_explicit_missing_directory_is_not_replaced(settings):
    before = settings.config_path.read_bytes()
    assert not settings.documents['noc'].output_dir.exists()
    loaded = DesktopConfig(settings.config_path).load()
    assert loaded.documents['noc'].output_dir == settings.documents['noc'].output_dir
    assert settings.config_path.read_bytes() == before


def test_frozen_templates_resolve_from_bundle_not_appdata(settings, tmp_path, monkeypatch):
    data = yaml.safe_load(settings.config_path.read_text(encoding='utf-8'))
    for config in data['documents'].values():
        config['template_path'] = 'templates/' + Path(config['template_path']).name
    settings.config_path.write_text(yaml.safe_dump(data), encoding='utf-8')
    bundle = tmp_path / 'extracted bundle'
    monkeypatch.setattr(runtime_paths, 'is_frozen', lambda: True)
    monkeypatch.setattr(runtime_paths, 'resource_root', lambda: bundle)
    loaded = DesktopConfig(settings.config_path).load()
    for key, config in loaded.documents.items():
        assert config.template_path == bundle / 'templates' / settings.documents[key].template_path.name
        assert config.output_dir == settings.documents[key].output_dir
    assert loaded.credentials_file == settings.credentials_file
    assert loaded.config_path == settings.config_path
    chosen = tmp_path / 'new folder'; chosen.mkdir()
    updated = DesktopConfig(settings.config_path).save_output('noc', chosen)
    assert updated.documents['noc'].output_dir == chosen
    # Persistence never writes ephemeral _MEIPASS paths into office YAML.
    assert yaml.safe_load(settings.config_path.read_text(encoding='utf-8'))['documents']['noc']['template_path'].startswith('templates/')


def test_bundled_template_traversal_rejected(settings, monkeypatch):
    data = yaml.safe_load(settings.config_path.read_text(encoding='utf-8'))
    data['documents']['noc']['template_path'] = '../outside.docx'
    settings.config_path.write_text(yaml.safe_dump(data), encoding='utf-8')
    monkeypatch.setattr(runtime_paths, 'is_frozen', lambda: True)
    with pytest.raises(SetupError): DesktopConfig(settings.config_path).load()


@pytest.mark.parametrize('content', [None, 'broken: [yaml', 'schema_version: 1', 'schema_version: 1\nschema_version: 2'])
def test_startup_config_errors_are_contained(tmp_path, monkeypatch, content):
    path = tmp_path / 'config.yaml'
    if content is not None: path.write_text(content, encoding='utf-8')
    labels = []
    monkeypatch.setattr(app.ttk, 'Label', lambda *a, **kw: labels.append(kw['text']) or Mock())
    root = Mock()
    assert app.create_application(root, DesktopConfig(path)) is None
    assert labels[0].startswith('Setup error')
    assert 'Traceback' not in labels[0]


def test_startup_has_no_generation_or_sheet_access(settings, monkeypatch):
    monkeypatch.setattr(app.ttk, 'Notebook', Mock())
    tabs = {'noc': Mock(), 'affidavit': Mock(), 'consent': Mock()}
    monkeypatch.setattr(app, 'build_tabs', Mock(return_value=tabs))
    worker = Mock(); monkeypatch.setattr(desktop.threading, 'Thread', worker)
    import sheets_service
    connect = Mock(side_effect=AssertionError('No startup networking'))
    monkeypatch.setattr(sheets_service, 'connect', connect)
    controller = app.create_application(Mock(), DesktopConfig(settings.config_path))
    assert controller.active_key is None
    worker.assert_not_called(); connect.assert_not_called()


def test_rotating_logs_and_secret_free_exceptions(settings, tmp_path, monkeypatch):
    monkeypatch.setattr(runtime_paths, 'desktop_log_path', lambda settings=None: tmp_path / 'logs' / 'generator.log')
    logger, handler = app.configure_desktop_logging(settings)
    try:
        try: raise RuntimeError('SECRET_PRIVATE_KEY_MATERIAL')
        except RuntimeError as exc: desktop.log_failure('generation failed', exc, 'noc')
    finally:
        logger.removeHandler(handler); handler.close()
    text = (tmp_path / 'logs' / 'generator.log').read_text(encoding='utf-8')
    assert 'noc generation failed' in text and 'RuntimeError' in text and 'test_desktop_runtime.py' in text
    assert 'SECRET_PRIVATE_KEY_MATERIAL' not in text
    assert handler.backupCount == 4


def test_installer_seed_is_redacted_and_valid_after_administrator_setup(tmp_path, monkeypatch):
    data = yaml.safe_load((ROOT / 'config.example.yaml').read_text(encoding='utf-8'))
    assert data['google']['spreadsheet_id'] == 'YOUR_SPREADSHEET_ID'
    assert 'private_key' not in str(data)
    data['google']['spreadsheet_id'] = 'synthetic_test_spreadsheet_0123456789'
    path = tmp_path / 'config.yaml'; path.write_text(yaml.safe_dump(data), encoding='utf-8')
    monkeypatch.setattr(runtime_paths, 'documents_directory', lambda: tmp_path / 'Documents')
    settings = DesktopConfig(path).load()
    assert {key: c.output_dir.name for key, c in settings.documents.items()} == {
        'noc': 'NOC Documents', 'affidavit': 'Affidavit Documents', 'consent': 'Consent Documents'}


def test_spec_explicit_bundle_contents_and_windowed_name(monkeypatch):
    # Execute the real spec with PyInstaller doubles; no binary build on macOS.
    hooks = types.ModuleType('PyInstaller.utils.hooks')
    hooks.collect_data_files = Mock(return_value=[])
    monkeypatch.setitem(sys.modules, 'PyInstaller.utils.hooks', hooks)
    monkeypatch.setattr(sys, 'platform', 'win32')
    analysis = Mock(return_value=SimpleNamespace(pure=[], scripts=[], binaries=[], datas=[]))
    executable = Mock()
    runpy.run_path(str(ROOT / 'legal_document_generator.spec'), init_globals={
        'SPECPATH': str(ROOT), 'Analysis': analysis, 'PYZ': Mock(), 'EXE': executable})
    entries = analysis.call_args.kwargs['datas']
    assert {Path(src).name for src, dest in entries} == {p.name for p in (ROOT / 'templates').glob('*.docx') if not p.name.startswith('~$')}
    assert all(Path(src).parent == ROOT / 'templates' and dest == 'templates' for src, dest in entries)
    assert executable.call_args.kwargs['console'] is False
    assert executable.call_args.kwargs['name'] == 'Legal Document Generator'
