from dataclasses import replace
import json
import subprocess
import sys

import pytest
import yaml

from config_manager import load_settings
from document_registry import SPECS
from document_generator import output_filename, preflight_template
from main import main
from processor import run_batch
from tests.extension_helpers import ROOT, configured
from tests.helpers import FakeSheet
from tests.test_registration import VALUES as REGISTRATION_VALUES
from tests.test_by_law import VALUES as BY_LAW_VALUES
from tests.test_form_a_registration import values as form_a_values

NEW_KEYS = ('registration', 'by_law', 'form_a_registration')
CONTRACTS = {
    'registration': ('Registration_Template.docx', 'Registration Responses', REGISTRATION_VALUES),
    'by_law': ('By_Law_Template.docx', 'By-Law Responses', BY_LAW_VALUES),
    'form_a_registration': ('Form_A_Registration_Template.docx', 'Form A Registration Responses', form_a_values()),
}


@pytest.fixture
def all_settings(settings):
    for key, (template, worksheet, _) in CONTRACTS.items():
        settings = configured(settings, SPECS[key], template, worksheet)
    return settings


def test_registry_complete_and_legacy_compatible(settings, all_settings):
    assert tuple(SPECS) == ('noc', 'affidavit', 'consent', *NEW_KEYS)
    # Older three-document YAML remains valid and does not enable new adapters.
    assert tuple(settings.documents) == ('affidavit', 'consent', 'noc')
    for key in SPECS:
        preflight_template(SPECS[key], all_settings.documents[key], all_settings)


@pytest.mark.parametrize('key', NEW_KEYS)
def test_captured_live_header_contract(key):
    from document_generator import heading_map
    from sheets_service import STATUS_COLUMNS
    headers = json.loads((ROOT / 'tests/fixtures/extension_headers.json').read_text(encoding='utf-8'))[key]
    assert headers[0] == 'Timestamp'
    assert headers[-4:] == list(STATUS_COLUMNS)
    mapping = heading_map(SPECS[key], headers)
    assert len(mapping) == len(SPECS[key].fields)
    assert list(mapping.values()) == list(range(1, len(SPECS[key].fields) + 1))


@pytest.mark.parametrize('key', NEW_KEYS)
def test_documented_mappings_match_adapter(key):
    text = (ROOT / 'FORM_SPEC.md').read_text(encoding='utf-8')
    titles = {'registration': 'Registration', 'by_law': 'By-Law', 'form_a_registration': 'Form-A'}
    section = text.split('## ' + titles[key] + ' explicit mappings\n')[1].split('\n## ')[0]
    rows = [line.split('|')[1:-1] for line in section.splitlines() if line.startswith('| ')][2:]
    assert len(rows) == len(SPECS[key].fields)
    for row, field in zip(rows, SPECS[key].fields):
        assert row[0].strip() == field.heading
        assert row[1].strip().strip('`') == field.parameter
        assert row[2].strip().strip('`') == field.placeholder
        assert (row[3].strip() == 'Yes') == field.required


@pytest.mark.parametrize('key', NEW_KEYS)
def test_shared_status_retry_and_no_cross_document_outputs(all_settings, key):
    data = CONTRACTS[key][2]
    records = [data, {**data, 'processing_status': ' eRrOr '},
               *[{**data, 'processing_status': status} for status in ('PROCESSING', 'GENERATED', 'other')], None]
    sheet = FakeSheet(key, records)
    before = [row.copy() for row in sheet.data]
    result = run_batch(all_settings, key, worksheet=sheet)
    assert result.counts['generated'] == 2 and result.counts['skipped'] == 4
    assert len(list(all_settings.documents[key].output_dir.glob('*.docx'))) == 2
    assert run_batch(all_settings, key, worksheet=sheet).counts['generated'] == 0
    for original, current in zip(before, sheet.data):
        assert original[:-4] == current[:-4]
    for other, config in all_settings.documents.items():
        if other != key:
            assert not config.output_dir.exists()


@pytest.mark.parametrize('key', NEW_KEYS)
def test_shared_cli_readonly_and_designated_dry_run(all_settings, monkeypatch, capsys, key):
    import main as cli
    import processor
    sheet = FakeSheet(key, [CONTRACTS[key][2]])
    before = [row.copy() for row in sheet.data]
    monkeypatch.setattr(cli, 'load_settings', lambda _: all_settings)
    monkeypatch.setattr(cli, 'connect', lambda *args: sheet)
    monkeypatch.setattr(processor, 'connect', lambda *args: sheet)
    assert main(['check-sheets', '--document', key]) == 0
    assert main(['generate', '--document', key, '--rows', '2', '--dry-run']) == 0
    assert 'would_generate=1' in capsys.readouterr().out
    assert sheet.data == before and sheet.writes == []
    assert not all_settings.documents[key].output_dir.exists()


@pytest.mark.parametrize('key', NEW_KEYS)
def test_invalid_dry_run_never_writes(all_settings, key):
    sheet = FakeSheet(key, [{**CONTRACTS[key][2], 'association_name': ''}])
    before = [row.copy() for row in sheet.data]
    result = run_batch(all_settings, key, rows=[2], dry_run=True, worksheet=sheet)
    assert result.counts['invalid'] == 1 and sheet.data == before and not sheet.writes
    assert not all_settings.documents[key].output_dir.exists()


@pytest.mark.parametrize('key', NEW_KEYS)
def test_filenames_are_safe_and_row_specific(all_settings, key):
    values = {**CONTRACTS[key][2], 'association_name': '../../CON\\<>:|?*' + 'परीक्षण' * 200}
    first = output_filename(all_settings.documents[key], values, 2)
    second = output_filename(all_settings.documents[key], values, 3)
    assert first != second and first.endswith('_2.docx')
    assert len(first.encode()) <= 230 and '..' not in first
    assert not set('/\\<>:|?*') & set(first)


def test_single_config_and_source_execution_from_other_directory(all_settings, config_data, tmp_path):
    for key in NEW_KEYS:
        config = all_settings.documents[key]
        config_data['documents'][key] = dict(
            enabled=True, label=config.label, worksheet_name=config.worksheet_name,
            template_path=str(config.template_path), output_dir=str(config.output_dir),
            filename_pattern=config.filename_pattern, input_date_format=config.input_date_format)
    path = tmp_path / 'six documents.yaml'
    path.write_text(yaml.safe_dump(config_data), encoding='utf-8')
    loaded = load_settings(path)
    assert set(loaded.documents) == set(SPECS)
    elsewhere = tmp_path / 'elsewhere'
    elsewhere.mkdir()
    # Run actual main.py source with network access replaced by offline Sheet
    # doubles. CLI still parses arguments, loads YAML and uses the real processor.
    script = '''
import sys, runpy, socket
sys.path.insert(0, sys.argv[1])
def blocked(*args, **kwargs): raise AssertionError('offline only')
socket.socket.connect = blocked
socket.create_connection = blocked
from tests.helpers import FakeSheet
from tests.test_extension_integration import CONTRACTS
import processor
key, config = sys.argv[2:4]
sheet = FakeSheet(key, [CONTRACTS[key][2]])
processor.connect = lambda *args: sheet
sys.argv = ['main.py', '--config', config, 'generate', '--document', key, '--rows', '2', '--dry-run']
try:
    runpy.run_path(sys.path[0] + '/main.py', run_name='__main__')
except SystemExit as exc:
    assert exc.code == 0
assert not sheet.writes
'''
    for key in NEW_KEYS:
        result = subprocess.run([sys.executable, '-c', script, str(ROOT), key, str(path)],
                                cwd=elsewhere, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        assert 'would_generate=1' in result.stdout
        assert not loaded.documents[key].output_dir.exists()
