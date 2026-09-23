from pathlib import Path
import socket
import pytest
import yaml
from config_manager import load_settings

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError('Network forbidden in offline tests')
    monkeypatch.setattr(socket.socket, 'connect', blocked)
    monkeypatch.setattr(socket, 'create_connection', blocked)


@pytest.fixture
def config_data():
    # Synthetic configuration; never reads the user's active settings or credentials.
    return {
        'schema_version': 1,
        'app': {'name': 'TEST Generator', 'log_file': 'logs/test.log', 'log_level': 'INFO'},
        'google': {'spreadsheet_id': 'synthetic_test_spreadsheet_0123456789', 'credentials_file': 'secrets/test-missing.json', 'scopes': ['https://www.googleapis.com/auth/spreadsheets']},
        'formatting': {'document_date_format': '%d-%m-%Y', 'processed_at_format': '%d-%m-%Y %H:%M:%S', 'blank_document_date': '..........'},
        'processing': {'error_message_max_length': 500},
        'documents': {key: {'enabled': True, 'label': key, 'worksheet_name': sheet, 'template_path': str(ROOT / 'templates' / template), 'output_dir': 'output with spaces/' + key, 'filename_pattern': key + '_{project_name}_{row_number}.docx', 'input_date_format': '%Y-%m-%d'} for key, sheet, template in [('noc','NOC Responses','Noc_Template.docx'), ('affidavit','Affidavit Responses','Affidavit_Template.docx'), ('consent','Consent Responses','Consent_Template.docx')]}}


@pytest.fixture
def settings(tmp_path, config_data):
    file = tmp_path / 'config.yaml'
    file.write_text(yaml.safe_dump(config_data), encoding='utf-8')
    return load_settings(file)
