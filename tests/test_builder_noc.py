"""Builder NOC through the existing project repository and attachment flow."""
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.parse import unquote
from zipfile import ZipFile
from xml.etree import ElementTree as ET

import pytest
from fastapi.testclient import TestClient

from document_generator import preflight_template, template_expressions, xml_parts
from documents.builder_noc import SPEC
from models import RowError
from web.app import create_app
from web.downloads import DOCX_TYPE, TEMPLATES, render_document
from web.mock_data import mock_repository
from web.schema import PROJECT_FIELDS, PROJECT_DOCUMENTS, MEMBER_DOCUMENTS
from web.services import document_state
from web.sheets_repository import SheetsProjectRepository, TABLES, encode

ROUTE = '/projects/demo/documents/builder_noc/generate'
REQUIRED = 'developer_company developer_address developer_name tehsil district_name association_name project_name association_address rera_registration_no completion_certificate_no completion_certificate_date'.split()
TEMPLATE = Path(__file__).resolve().parents[1] / 'templates' / 'Builder_NOC_Template.docx'


@pytest.fixture
def client():
    with TestClient(create_app()) as client:
        yield client


def document_text(data):
    parts = xml_parts(BytesIO(data))
    return '\n'.join(text for name, text in parts.items() if name.endswith('.xml'))


def test_template_and_existing_field_contract():
    assert {f.parameter for f in SPEC.fields} == set(REQUIRED)
    assert all(f.required and f.placeholder == f.parameter for f in SPEC.fields)
    assert set(REQUIRED) <= {f.key for f in PROJECT_FIELDS}
    assert set(template_expressions(xml_parts(TEMPLATE))) == set(REQUIRED)
    assert 'document_date' not in {f.parameter for f in SPEC.fields}
    preflight_template(SPEC, SimpleNamespace(template_path=TEMPLATE, input_date_format='%Y-%m-%d'),
                       SimpleNamespace(document_date_format='%d-%m-%Y', blank_document_date='..........'))


def test_seventh_document_visible_in_existing_pages(client):
    assert len(PROJECT_DOCUMENTS) + len(MEMBER_DOCUMENTS) == 7
    assert PROJECT_DOCUMENTS['builder_noc'] == 'Builder NOC'
    for path in ('/projects/demo', '/projects/demo/documents'):
        assert 'Builder NOC' in client.get(path).text
    assert f'action="{ROUTE}"' in client.get('/projects/demo/documents').text
    assert '5 project document types' in client.get('/projects').text


def test_download_maps_all_project_values_and_keeps_printed_date(client):
    repo = client.app.state.repository
    project = repo.get('demo')
    project.details['association_address'] = 'ग्राम परीक्षण, खसरा नं. 123/4 एवं 005/6'
    project.details['developer_company'] = 'TEST Company & Partners <Firm>'
    project.committee_members.clear()
    project.members.clear()
    project.details['project_location'] = ''  # Builder NOC uses the association address.
    repo.save(project)
    response = client.post(ROUTE)
    assert response.status_code == 200
    assert response.headers['content-type'] == DOCX_TYPE
    assert unquote(response.headers['content-disposition']) == "attachment; filename*=UTF-8''builder_noc_TEST_Sample_Gardens.docx"
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['x-content-type-options'] == 'nosniff'
    text = document_text(response.content)
    for key in REQUIRED:
        expected = '15-01-2025' if key == 'completion_certificate_date' else project.details[key]
        assert expected in text, key
    assert 'दिनांक:------------' in text
    assert not any(token in text for token in ('{{', '}}', '{%', '%}'))
    with ZipFile(TEMPLATE) as source, ZipFile(BytesIO(response.content)) as output:
        for name in source.namelist():
            if name.startswith('word/media/'):
                assert source.read(name) == output.read(name)
            elif name in ('word/styles.xml', 'word/fontTable.xml'):
                assert ET.canonicalize(source.read(name)) == ET.canonicalize(output.read(name))
    assert repo.get('demo').generated == {'builder_noc'}
    assert client.post(ROUTE).headers['content-type'] == DOCX_TYPE
    assert repo.get('demo').generated == {'builder_noc'}


@pytest.mark.parametrize('field', REQUIRED)
def test_each_required_value_blocks_download(client, field, monkeypatch):
    repo = client.app.state.repository
    project = repo.get('demo')
    project.details[field] = ''
    # Inject an incomplete read; normal saves already reject blank project names.
    monkeypatch.setattr(repo, 'get', lambda project_id: project)
    with pytest.raises(RowError, match=field):
        render_document(project, 'builder_noc')
    assert document_state(project, 'builder_noc')['status'] == 'Missing Data'
    response = client.post(ROUTE)
    assert 'Cannot generate:' in response.text
    assert 'content-disposition' not in response.headers
    assert not repo.get('demo').generated


@pytest.mark.parametrize('field,value', [('completion_certificate_date', '2025-02-30'),
                                         ('developer_name', '{{ unsafe }}'),
                                         ('association_address', '\x01invalid')])
def test_invalid_input_uses_existing_error_handling(client, field, value):
    repo = client.app.state.repository
    project = repo.get('demo')
    project.details[field] = value
    repo.save(project)
    response = client.post(ROUTE)
    assert 'Cannot generate:' in response.text
    assert not repo.get('demo').generated


def test_missing_template_uses_existing_render_error(client, monkeypatch):
    monkeypatch.setitem(TEMPLATES, 'builder_noc', 'missing-builder-template.docx')
    response = client.post(ROUTE)
    assert 'DOCX rendering failed' in response.text
    assert not client.app.state.repository.get('demo').generated


def test_no_output_folder_write(client, monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError('Browser downloads must not write files')
    monkeypatch.setattr(Path, 'mkdir', blocked)
    monkeypatch.setattr(Path, 'write_bytes', blocked)
    monkeypatch.setattr('document_generator.save_atomic', blocked)
    assert client.post(ROUTE).headers['content-type'] == DOCX_TYPE


def test_sheets_repository_download_and_revision_without_schema_writes():
    project = mock_repository().get('demo')
    project.details['developer_name'] = 'UI PROJECTS DEVELOPER'
    rows = encode(project)
    book = Mock()
    # Read the real normalized repository format, including existing headers.
    book.fetch_sheet_metadata.return_value = {'sheets': [
        {'properties': {'title': name, 'sheetId': index, 'sheetType': 'GRID',
                        'gridProperties': {'rowCount': 100, 'columnCount': len(headers)}},
         'data': [{'startRow': 0, 'rowData': [
             {'values': [{'userEnteredValue': {'stringValue': value}} for value in row]}
             for row in [list(headers), *rows[name]]]}]}
        for index, (name, headers) in enumerate(TABLES.items(), 1)
    ]}
    repo = SheetsProjectRepository(lambda: book)
    with TestClient(create_app(repository=repo)) as client:
        assert client.post(ROUTE, data={'_revision': 'stale'}).status_code == 409
        revision = repo.get('demo').revision
        response = client.post(ROUTE, data={'_revision': revision})
        assert response.status_code == 200
        assert 'UI PROJECTS DEVELOPER' in document_text(response.content)
        assert repo.get('demo').generated == {'builder_noc'}
    book.batch_update.assert_not_called()
    assert set(TABLES) == {'UI Projects', 'UI Members', 'UI Committee'}
    assert len(TABLES['UI Projects']) == 26


def test_unknown_project_is_not_generated(client):
    assert client.post(ROUTE.replace('/demo/', '/missing/')).status_code == 404
