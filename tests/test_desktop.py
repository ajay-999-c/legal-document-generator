"""Offline GUI architecture tests: real controller and view code, no display/cloud."""
from dataclasses import replace
from pathlib import Path
from threading import Event, Thread, get_ident
from unittest.mock import Mock
import pytest
import yaml
import desktop
from desktop import DesktopController, DocumentTab, build_tabs
from desktop_config import DesktopConfig
from models import BatchResult, RowOutcome, SetupError


class Root:
    def __init__(self):
        self.owner = get_ident()
        self.callbacks = {}
        self.destroyed = False

    def after(self, delay, callback):
        assert get_ident() == self.owner
        self.callbacks[len(self.callbacks) + 1] = callback
        return len(self.callbacks)

    def after_cancel(self, identifier):
        assert get_ident() == self.owner
        self.callbacks.pop(identifier, None)

    def destroy(self):
        self.destroyed = True


class Tab:
    def __init__(self, parent=None, metadata=None, *callbacks):
        self.owner = get_ident()
        self.metadata = metadata
        self.status = 'Ready'
        self.counts = {}
        self.enabled = True
        self.folder = metadata.output_dir if metadata else None
        self.updates = []

    def update(self, name, value):
        assert get_ident() == self.owner
        setattr(self, name, value)
        self.updates.append((name, value))

    def set_enabled(self, value): self.update('enabled', value)
    def set_status(self, value): self.update('status', value)
    def set_counts(self, value): self.update('counts', value)
    def set_folder(self, value): self.update('folder', value)


@pytest.fixture
def controller(settings):
    root = Root()
    store = DesktopConfig(settings.config_path)
    tabs = build_tabs(Mock(), settings, Mock(), Mock(), Mock(), tab_factory=Tab)
    return DesktopController(root, store, settings, tabs)


def wait_for_job(controller):
    controller.worker.join(timeout=5)
    assert not controller.worker.is_alive()
    controller.poll()


def test_registry_tabs_and_independent_folders(settings):
    notebook = Mock()
    tabs = build_tabs(notebook, settings, Mock(), Mock(), Mock(), tab_factory=Tab)
    assert list(tabs) == ['noc', 'affidavit', 'consent']
    assert notebook.add.call_count == 3
    for key, tab in tabs.items():
        assert tab.folder == settings.documents[key].output_dir
        assert not hasattr(tab.metadata, 'template_path')
    disabled = replace(settings, documents={**settings.documents, 'consent': replace(settings.documents['consent'], enabled=False)})
    assert list(build_tabs(Mock(), disabled, Mock(), Mock(), Mock(), tab_factory=Tab)) == ['noc', 'affidavit']


def test_future_registry_document(settings, monkeypatch):
    monkeypatch.setitem(desktop.SPECS, 'fourth', replace(desktop.SPECS['noc'], key='fourth'))
    settings = replace(settings, documents={**settings.documents, 'fourth': replace(settings.documents['noc'], key='fourth', label='Fourth', output_dir=Path('/fourth'))})
    tabs = build_tabs(Mock(), settings, Mock(), Mock(), Mock(), tab_factory=Tab)
    assert tabs['fourth'].metadata.label == 'Fourth'


def test_browse_persists_exact_folder_and_preserves_other_settings(controller, tmp_path):
    before = yaml.safe_load(controller.store.path.read_text())
    chosen = tmp_path / 'Office output'; chosen.mkdir()
    controller.choose_folder = Mock(return_value=str(chosen))
    controller.browse('noc')
    after = yaml.safe_load(controller.store.path.read_text())
    expected = before.copy()
    before['documents']['noc']['output_dir'] = str(chosen)
    assert after == expected
    assert controller.tabs['noc'].folder == chosen
    assert controller.settings.documents['affidavit'].output_dir == controller.tabs['affidavit'].folder
    assert controller.settings.documents['noc'].output_dir == chosen
    controller.choose_folder.assert_called_once()


def test_browse_cancel_does_not_write(controller):
    original = controller.store.path.read_bytes()
    controller.choose_folder = Mock(return_value='')
    controller.browse('noc')
    assert controller.store.path.read_bytes() == original


@pytest.mark.parametrize('failure', ['duplicate', 'replace', 'missing'])
def test_folder_failure_preserves_config(controller, monkeypatch, tmp_path, failure):
    original = controller.store.path.read_bytes()
    chosen = tmp_path / 'new'; chosen.mkdir()
    if failure == 'duplicate':
        chosen = controller.settings.documents['consent'].output_dir
        chosen.mkdir(parents=True)
    elif failure == 'missing':
        chosen = tmp_path / 'absent'
    else:
        monkeypatch.setattr(Path, 'replace', Mock(side_effect=PermissionError('private details')))
    controller.choose_folder = Mock(return_value=str(chosen))
    controller.browse('noc')
    assert controller.store.path.read_bytes() == original
    assert not list(tmp_path.glob('.config-*'))
    assert 'Could not save folder' in controller.tabs['noc'].status
    assert 'private' not in controller.tabs['noc'].status


@pytest.mark.parametrize('key', ['noc', 'affidavit', 'consent'])
def test_worker_routes_key_and_only_selected_results(controller, key):
    calls = []
    def process(settings, selected, progress):
        calls.append((selected, get_ident(), settings.documents[selected].output_dir))
        progress(RowOutcome(2, 'generated'))
        return BatchResult(selected, False, [RowOutcome(2, 'generated')])
    controller.processor = process
    assert controller.generate(key)
    wait_for_job(controller)
    assert calls == [(key, controller.worker.ident, controller.settings.documents[key].output_dir)]
    assert controller.worker.ident != get_ident()
    assert controller.tabs[key].counts['generated'] == 1
    assert controller.tabs[key].status == 'Generation complete'
    for other, tab in controller.tabs.items():
        assert tab.enabled
        if other != key:
            assert tab.status == 'Ready' and tab.counts == {}


@pytest.mark.parametrize('exception, prefix', [(SetupError('private details'), 'Setup error'), (OSError('private details'), 'Generation failed')])
def test_worker_failure_restores_all_controls(controller, exception, prefix):
    controller.processor = Mock(side_effect=exception)
    controller.generate('affidavit')
    wait_for_job(controller)
    assert all(t.enabled for t in controller.tabs.values())
    assert controller.tabs['affidavit'].status.startswith(prefix)
    assert 'private' not in controller.tabs['affidavit'].status
    assert controller.active_key is None


def test_one_job_and_all_controls_disabled_until_main_thread_drains(controller):
    release = Event()
    calls = []
    def process(settings, key, progress):
        calls.append(key)
        assert release.wait(5)
        return BatchResult(key, False)
    controller.processor = process
    try:
        assert controller.generate('noc')
        assert not any(t.enabled for t in controller.tabs.values())
        assert not controller.generate('consent')
        controller.choose_folder = Mock()
        controller.browse('affidavit')
        controller.choose_folder.assert_not_called()
    finally:
        release.set()
    controller.worker.join(timeout=5)
    assert not any(t.enabled for t in controller.tabs.values())
    controller.poll()
    assert calls == ['noc'] and all(t.enabled for t in controller.tabs.values())


def test_ui_calls_reject_worker_thread(controller):
    errors = []
    def wrong_thread():
        try: controller.generate('noc')
        except RuntimeError as exc: errors.append(str(exc))
    thread = Thread(target=wrong_thread); thread.start(); thread.join()
    assert errors == ['Desktop UI operation must run on the main thread.']


def test_thread_start_failure_restores_controls(controller, monkeypatch):
    monkeypatch.setattr(desktop.threading.Thread, 'start', Mock(side_effect=RuntimeError('cannot start')))
    controller.generate('noc')
    assert controller.active_key is None
    assert all(tab.enabled for tab in controller.tabs.values())


@pytest.mark.parametrize('outcome', ['failed', 'sync_failed', 'changed', 'invalid'])
def test_partial_errors_and_sync_feedback(controller, outcome):
    row = RowOutcome(3, outcome, synchronization_errors=['ERROR synchronization failed.'])
    controller.processor = Mock(return_value=BatchResult('noc', False, [RowOutcome(2, 'generated'), row]))
    controller.generate('noc'); wait_for_job(controller)
    assert controller.tabs['noc'].counts['generated'] == 1
    assert controller.tabs['noc'].counts['failed'] == 1
    assert 'Sheet updates need review' in controller.tabs['noc'].status


def test_config_changed_before_job_is_blocked(controller):
    data = yaml.safe_load(controller.store.path.read_text())
    data['documents']['noc']['output_dir'] = 'changed'
    controller.store.path.write_text(yaml.safe_dump(data))
    controller.processor = Mock()
    controller.generate('noc')
    controller.processor.assert_not_called()
    assert controller.tabs['noc'].status.startswith('Setup error')
    assert all(tab.enabled for tab in controller.tabs.values())


def test_open_selected_folder_and_failure(controller):
    controller.opener = Mock()
    controller.open('consent')
    controller.opener.assert_called_once_with(controller.settings.documents['consent'].output_dir)
    controller.opener.side_effect = OSError('private details')
    controller.open('consent')
    assert controller.tabs['consent'].status.startswith('Could not open folder')


@pytest.mark.parametrize('platform, command', [('darwin', 'open'), ('linux', 'xdg-open'), ('win32', None)])
def test_platform_open_folder(monkeypatch, tmp_path, platform, command):
    monkeypatch.setattr(desktop.sys, 'platform', platform)
    start = Mock(); run = Mock()
    monkeypatch.setattr(desktop.os, 'startfile', start, raising=False)
    monkeypatch.setattr(desktop.subprocess, 'run', run)
    desktop.open_folder(tmp_path)
    if command:
        assert run.call_args.args[0] == [command, str(tmp_path)]
        start.assert_not_called()
    else:
        start.assert_called_once_with(str(tmp_path))
        run.assert_not_called()


def test_missing_folder_does_not_launch(monkeypatch, tmp_path):
    run = Mock(); monkeypatch.setattr(desktop.subprocess, 'run', run)
    with pytest.raises(OSError): desktop.open_folder(tmp_path / 'absent')
    run.assert_not_called()


def test_close_waits_for_generation(controller, monkeypatch):
    dialog = Mock(); monkeypatch.setattr(desktop.messagebox, 'showinfo', dialog)
    controller.active_key = 'noc'
    assert not controller.close() and not controller.root.destroyed
    dialog.assert_called_once()
    controller.active_key = None
    assert controller.close() and controller.root.destroyed


def test_real_tab_widget_construction_has_no_template_text(settings, monkeypatch):
    # Execute DocumentTab.__init__ with display-free widget doubles, inspecting
    # actual labels/callback wiring rather than a duplicate UI specification.
    widgets = []
    class Widget:
        def __init__(self, *args, **kwargs):
            self.options = kwargs
            widgets.append(self)
        def grid(self, **kwargs): pass
        def configure(self, **kwargs): self.options.update(kwargs)
    class Variable:
        def __init__(self, master, value): self.value = value
        def set(self, value): self.value = value
    monkeypatch.setattr(desktop.ttk.Frame, '__init__', lambda *a, **kw: None)
    monkeypatch.setattr(DocumentTab, 'columnconfigure', lambda *a, **kw: None)
    for name in ('Label', 'Entry', 'Button', 'Frame'):
        monkeypatch.setattr(desktop.ttk, name, Widget)
    monkeypatch.setattr(desktop.tk, 'StringVar', Variable)
    generate, browse, opened = Mock(), Mock(), Mock()
    tab = DocumentTab(None, desktop.tab_metadata(settings)[0], generate, browse, opened)
    labels = [w.options.get('text', '') for w in widgets]
    assert 'Generate Documents' in labels and 'Save Folder' in labels
    assert not any('template' in text.lower() or '.docx' in text.lower() for text in labels)
    tab.generate_button.options['command'](); generate.assert_called_once_with('noc')
    tab.browse_button.options['command'](); browse.assert_called_once_with('noc')
    tab.set_enabled(False)
    assert tab.generate_button.options['state'] == 'disabled'
    assert tab.browse_button.options['state'] == 'disabled'
    assert next(w for w in widgets if 'textvariable' in w.options and w.options.get('state') == 'readonly')


@pytest.mark.parametrize('key', ['noc', 'affidavit', 'consent'])
def test_gui_integrates_with_unchanged_shared_processor(controller, monkeypatch, key):
    import processor
    from tests.helpers import FakeSheet
    sheet = FakeSheet(key)
    connect = Mock(return_value=sheet)
    monkeypatch.setattr(processor, 'connect', connect)
    controller.generate(key)
    wait_for_job(controller)
    connect.assert_called_once_with(controller.settings, controller.settings.documents[key])
    assert controller.tabs[key].counts['generated'] == 1
    assert sheet.data[1][-4] == 'GENERATED'
    assert len(list(controller.settings.documents[key].output_dir.glob('*.docx'))) == 1
    for other, config in controller.settings.documents.items():
        if other != key: assert not config.output_dir.exists()


@pytest.mark.parametrize('problem', ['template', 'mapping', 'output', 'credentials'])
def test_backend_setup_failures_are_contained_by_gui(controller, monkeypatch, problem):
    import processor
    from tests.helpers import FakeSheet
    sheet = FakeSheet('noc')
    if problem != 'credentials':
        monkeypatch.setattr(processor, 'connect', Mock(return_value=sheet))
    if problem == 'template':
        data = yaml.safe_load(controller.store.path.read_text())
        data['documents']['noc']['template_path'] = 'absent.docx'
        controller.store.path.write_text(yaml.safe_dump(data))
        controller.settings = controller.store.load()
    if problem == 'mapping': sheet.data[0][1] = 'Wrong heading'
    if problem == 'output':
        output = controller.settings.documents['noc'].output_dir
        output.parent.mkdir(parents=True); output.write_text('not a directory')
    controller.generate('noc'); wait_for_job(controller)
    assert controller.tabs['noc'].status.startswith('Setup error')
    assert all(tab.enabled for tab in controller.tabs.values())
    assert controller.tabs['consent'].status == 'Ready'
    assert not sheet.writes


def test_missing_config_on_generate_restores_controls(controller):
    controller.store.path.unlink()
    controller.processor = Mock()
    controller.generate('noc')
    controller.processor.assert_not_called()
    assert controller.tabs['noc'].status.startswith('Setup error')
    assert all(tab.enabled for tab in controller.tabs.values())
