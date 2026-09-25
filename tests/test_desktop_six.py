"""Six-document desktop coverage; all generation uses synthetic/fake Sheets."""
from dataclasses import replace
from threading import Event
from unittest.mock import Mock
import pytest
import yaml

import desktop
from config_manager import load_settings
from desktop import DesktopController, build_tabs
from desktop_config import DesktopConfig
from document_registry import SPECS
from models import BatchResult, RowOutcome
from tests.conftest import ROOT
from tests.test_desktop import Root, Tab, wait_for_job
from tests.test_extension_integration import CONTRACTS

KEYS = ('noc', 'affidavit', 'consent', 'registration', 'by_law', 'form_a_registration')
LABELS = ('NOC', 'Affidavit', 'Consent', 'Registration', 'By-Law', 'Form-A Registration')


def six_config(data):
    for key, (template, worksheet, _) in CONTRACTS.items():
        data['documents'][key] = dict(enabled=True, label=key, worksheet_name=worksheet,
            template_path=str(ROOT / 'templates' / template), output_dir='output with spaces/' + key,
            filename_pattern=key + '_{association_name}_{row_number}.docx', input_date_format='%Y-%m-%d')
    for key, label in zip(KEYS, LABELS):
        data['documents'][key]['label'] = label
    return data


@pytest.fixture
def six_settings(tmp_path, config_data):
    path = tmp_path / 'config.yaml'
    path.write_text(yaml.safe_dump(six_config(config_data)), encoding='utf-8')
    return load_settings(path)


@pytest.fixture
def six_controller(six_settings):
    tabs = build_tabs(Mock(), six_settings, Mock(), Mock(), Mock(), tab_factory=Tab)
    return DesktopController(Root(), DesktopConfig(six_settings.config_path), six_settings, tabs)


def test_six_tabs_labels_and_order_ignore_config_order(six_settings):
    # Registry order comes from its explicit tuple, independent of YAML ordering.
    settings = replace(six_settings, documents=dict(reversed(list(six_settings.documents.items()))))
    notebook = Mock()
    tabs = build_tabs(notebook, settings, Mock(), Mock(), Mock(), tab_factory=Tab)
    assert tuple(SPECS) == KEYS
    assert tuple(tabs) == KEYS and notebook.add.call_count == 6
    assert tuple(c.kwargs['text'] for c in notebook.add.call_args_list) == LABELS
    for key, tab in tabs.items():
        assert tab.folder == six_settings.documents[key].output_dir
        assert not hasattr(tab.metadata, 'template_path')


@pytest.mark.parametrize('key', KEYS)
def test_six_folder_persistence_is_independent(six_controller, tmp_path, key):
    c = six_controller
    before = yaml.safe_load(c.store.path.read_text(encoding='utf-8'))
    chosen = tmp_path / ('कार्यालय ' + key); chosen.mkdir()
    c.choose_folder = Mock(return_value=str(chosen))
    c.browse(key)
    before['documents'][key]['output_dir'] = str(chosen)
    assert yaml.safe_load(c.store.path.read_text(encoding='utf-8')) == before
    assert c.store.load().documents[key].output_dir == chosen
    assert c.tabs[key].folder == chosen
    for other in KEYS:
        assert c.tabs[other].folder == c.settings.documents[other].output_dir


@pytest.mark.parametrize('key', KEYS)
def test_six_buttons_actual_widget_wiring(six_settings, monkeypatch, key):
    widgets = []
    class Widget:
        def __init__(self, *a, **kw): self.options = kw; widgets.append(self)
        def grid(self, **kw): pass
        def configure(self, **kw): self.options.update(kw)
    class Variable:
        def __init__(self, master, value): self.value = value
        def set(self, value): self.value = value
    monkeypatch.setattr(desktop.ttk.Frame, '__init__', lambda *a, **kw: None)
    monkeypatch.setattr(desktop.DocumentTab, 'columnconfigure', lambda *a, **kw: None)
    for name in ('Label', 'Entry', 'Button', 'Frame'): monkeypatch.setattr(desktop.ttk, name, Widget)
    monkeypatch.setattr(desktop.tk, 'StringVar', Variable)
    generate, browse, opened = Mock(), Mock(), Mock()
    metadata = next(m for m in desktop.tab_metadata(six_settings) if m.key == key)
    tab = desktop.DocumentTab(None, metadata, generate, browse, opened)
    texts = [w.options.get('text', '') for w in widgets]
    assert metadata.label in texts
    assert not any(any(s in text.lower() for s in ('template', '.docx', 'worksheet', 'credentials', 'spreadsheet', 'backend')) for text in texts)
    tab.generate_button.options['command'](); generate.assert_called_once_with(key)
    tab.browse_button.options['command'](); browse.assert_called_once_with(key)
    next(w for w in widgets if w.options.get('text') == 'Open Generated Folder').options['command']()
    opened.assert_called_once_with(key)


@pytest.mark.parametrize('key', KEYS)
def test_six_shared_processor_routing_and_results(six_controller, monkeypatch, key):
    from tests.helpers import FakeSheet, values
    import processor
    data = CONTRACTS[key][2] if key in CONTRACTS else values(key)
    sheet = FakeSheet(key, [data])
    connect = Mock(return_value=sheet); monkeypatch.setattr(processor, 'connect', connect)
    c = six_controller
    assert c.generate(key)
    wait_for_job(c)
    connect.assert_called_once_with(c.settings, c.settings.documents[key])
    assert c.tabs[key].counts['generated'] == 1
    assert all(t.enabled for t in c.tabs.values())
    for other, tab in c.tabs.items():
        if other != key: assert tab.status == 'Ready' and tab.counts == {}


@pytest.mark.parametrize('key', KEYS)
@pytest.mark.parametrize('fails', [False, True])
def test_six_global_lock_and_restore(six_controller, key, fails):
    c = six_controller; release = Event(); calls = []
    def process(settings, selected, progress):
        calls.append(selected)
        assert release.wait(5)
        if fails: raise OSError('private server payload')
        return BatchResult(selected, False, [RowOutcome(2, 'generated')])
    c.processor = process
    try:
        assert c.generate(key)
        assert not any(t.enabled for t in c.tabs.values())
        for other in KEYS: assert not c.generate(other)
    finally: release.set()
    wait_for_job(c)
    assert calls == [key] and c.active_key is None and all(t.enabled for t in c.tabs.values())
    assert c.tabs[key].status.startswith('Generation failed' if fails else 'Generation complete')
    assert 'private' not in c.tabs[key].status
    for other, tab in c.tabs.items():
        if other != key: assert tab.status == 'Ready'
